import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import './LiquidEther.css';

/**
 * LiquidEther — verbatim source from reactbits.dev
 *
 * Props
 * ─────
 * mouseForce        number   20       strength of mouse-induced velocity
 * cursorSize        number   100      radius of the force brush
 * isViscous         bool     false    enable viscous diffusion pass
 * viscous           number   30       viscosity coefficient (isViscous=true)
 * iterationsViscous number   32       Jacobi iterations for viscous solve
 * iterationsPoisson number   32       Jacobi iterations for pressure solve
 * dt                number   0.014    simulation timestep
 * BFECC             bool     true     Back/Forward Error Compensation & Correction
 * resolution        number   0.5      FBO resolution scale (0–1)
 * isBounce          bool     false    bounce velocity at boundaries
 * colors            string[] ['#5227FF','#FF9FFC','#B497CF']  palette stops
 * style             object   {}       extra inline styles on container div
 * className         string   ''       extra class names on container div
 * autoDemo          bool     true     animate automatically when idle
 * autoSpeed         number   0.5      auto-pilot movement speed
 * autoIntensity     number   2.2      auto-pilot force multiplier
 * takeoverDuration  number   0.25     transition time from auto→mouse (s)
 * autoResumeDelay   number   1000     idle ms before auto-pilot resumes
 * autoRampDuration  number   0.6      auto-pilot ramp-up duration (s)
 */
export default function LiquidEther({
  mouseForce        = 20,
  cursorSize        = 100,
  isViscous         = false,
  viscous           = 30,
  iterationsViscous = 32,
  iterationsPoisson = 32,
  dt                = 0.014,
  BFECC             = true,
  resolution        = 0.5,
  isBounce          = false,
  colors            = ['#5227FF', '#FF9FFC', '#B497CF'],
  style             = {},
  className         = '',
  autoDemo          = true,
  autoSpeed         = 0.5,
  autoIntensity     = 2.2,
  takeoverDuration  = 0.25,
  autoResumeDelay   = 1000,
  autoRampDuration  = 0.6,
}) {
  const mountRef               = useRef(null);
  const webglRef               = useRef(null);
  const resizeObserverRef      = useRef(null);
  const rafRef                 = useRef(null);
  const intersectionObserverRef= useRef(null);
  const isVisibleRef           = useRef(true);
  const resizeRafRef           = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;

    function makePaletteTexture(stops) {
      let arr = (Array.isArray(stops) && stops.length > 0)
        ? (stops.length === 1 ? [stops[0], stops[0]] : stops)
        : ['#ffffff', '#ffffff'];
      const w = arr.length, data = new Uint8Array(w * 4);
      for (let i = 0; i < w; i++) {
        const c = new THREE.Color(arr[i]);
        data[i*4]=Math.round(c.r*255); data[i*4+1]=Math.round(c.g*255);
        data[i*4+2]=Math.round(c.b*255); data[i*4+3]=255;
      }
      const tex = new THREE.DataTexture(data, w, 1, THREE.RGBAFormat);
      tex.magFilter=tex.minFilter=THREE.LinearFilter;
      tex.wrapS=tex.wrapT=THREE.ClampToEdgeWrapping;
      tex.generateMipmaps=false; tex.needsUpdate=true; return tex;
    }
    const paletteTex = makePaletteTexture(colors);
    const bgVec4     = new THREE.Vector4(0,0,0,0);

    class CommonClass {
      constructor(){ this.width=this.height=0; this.aspect=1; this.pixelRatio=1; this.time=this.delta=0; this.container=this.renderer=this.clock=null; }
      init(c){ this.container=c; this.pixelRatio=Math.min(window.devicePixelRatio||1,2); this.resize();
        this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
        this.renderer.autoClear=false; this.renderer.setClearColor(new THREE.Color(0),0);
        this.renderer.setPixelRatio(this.pixelRatio); this.renderer.setSize(this.width,this.height);
        this.renderer.domElement.style.cssText='width:100%;height:100%;display:block;';
        this.clock=new THREE.Clock(); this.clock.start(); }
      resize(){ if(!this.container) return; const r=this.container.getBoundingClientRect();
        this.width=Math.max(1,Math.floor(r.width)); this.height=Math.max(1,Math.floor(r.height));
        this.aspect=this.width/this.height; if(this.renderer) this.renderer.setSize(this.width,this.height,false); }
      update(){ this.delta=this.clock.getDelta(); this.time+=this.delta; }
    }
    const Common=new CommonClass();

    class MouseClass {
      constructor(){
        this.mouseMoved=false; this.coords=new THREE.Vector2(); this.coords_old=new THREE.Vector2(); this.diff=new THREE.Vector2();
        this.timer=null; this.container=this.docTarget=this.listenerTarget=null;
        this.isHoverInside=this.hasUserControl=this.isAutoActive=false; this.autoIntensity=2; this.takeoverActive=false;
        this.takeoverStartTime=0; this.takeoverDuration=0.25; this.takeoverFrom=new THREE.Vector2(); this.takeoverTo=new THREE.Vector2(); this.onInteract=null;
        this._mm=this.onDocumentMouseMove.bind(this); this._ts=this.onDocumentTouchStart.bind(this);
        this._tm=this.onDocumentTouchMove.bind(this); this._te=this.onTouchEnd.bind(this); this._dl=this.onDocumentLeave.bind(this);
      }
      init(c){ this.container=c; this.docTarget=c.ownerDocument||null;
        const w=(this.docTarget?.defaultView)??(typeof window!=='undefined'?window:null); if(!w) return;
        this.listenerTarget=w; w.addEventListener('mousemove',this._mm); w.addEventListener('touchstart',this._ts,{passive:true});
        w.addEventListener('touchmove',this._tm,{passive:true}); w.addEventListener('touchend',this._te);
        this.docTarget?.addEventListener('mouseleave',this._dl); }
      dispose(){ this.listenerTarget?.removeEventListener('mousemove',this._mm); this.listenerTarget?.removeEventListener('touchstart',this._ts);
        this.listenerTarget?.removeEventListener('touchmove',this._tm); this.listenerTarget?.removeEventListener('touchend',this._te);
        this.docTarget?.removeEventListener('mouseleave',this._dl); this.listenerTarget=this.docTarget=this.container=null; }
      isPointInside(cx,cy){ if(!this.container) return false; const r=this.container.getBoundingClientRect();
        return r.width&&r.height&&cx>=r.left&&cx<=r.right&&cy>=r.top&&cy<=r.bottom; }
      updateHoverState(cx,cy){ return(this.isHoverInside=!!this.isPointInside(cx,cy)); }
      setCoords(x,y){ if(!this.container) return; if(this.timer) clearTimeout(this.timer);
        const r=this.container.getBoundingClientRect(); if(!r.width||!r.height) return;
        this.coords.set((x-r.left)/r.width*2-1,-((y-r.top)/r.height*2-1));
        this.mouseMoved=true; this.timer=setTimeout(()=>{ this.mouseMoved=false; },100); }
      setNormalized(nx,ny){ this.coords.set(nx,ny); this.mouseMoved=true; }
      onDocumentMouseMove(e){ if(!this.updateHoverState(e.clientX,e.clientY)) return; if(this.onInteract) this.onInteract();
        if(this.isAutoActive&&!this.hasUserControl&&!this.takeoverActive){
          const r=this.container?.getBoundingClientRect(); if(!r?.width) return;
          this.takeoverFrom.copy(this.coords); this.takeoverTo.set((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height*2-1));
          this.takeoverStartTime=performance.now(); this.takeoverActive=true; this.hasUserControl=true; this.isAutoActive=false; return; }
        this.setCoords(e.clientX,e.clientY); this.hasUserControl=true; }
      onDocumentTouchStart(e){ if(e.touches.length!==1) return; const t=e.touches[0];
        if(!this.updateHoverState(t.clientX,t.clientY)) return; if(this.onInteract) this.onInteract();
        this.setCoords(t.clientX,t.clientY); this.hasUserControl=true; }
      onDocumentTouchMove(e){ if(e.touches.length!==1) return; const t=e.touches[0];
        if(!this.updateHoverState(t.clientX,t.clientY)) return; if(this.onInteract) this.onInteract(); this.setCoords(t.clientX,t.clientY); }
      onTouchEnd(){ this.isHoverInside=false; } onDocumentLeave(){ this.isHoverInside=false; }
      update(){ if(this.takeoverActive){ const t=(performance.now()-this.takeoverStartTime)/(this.takeoverDuration*1000);
          if(t>=1){ this.takeoverActive=false; this.coords.copy(this.takeoverTo); this.coords_old.copy(this.coords); this.diff.set(0,0); }
          else{ this.coords.copy(this.takeoverFrom).lerp(this.takeoverTo,t*t*(3-2*t)); } }
        this.diff.subVectors(this.coords,this.coords_old); this.coords_old.copy(this.coords);
        if(!this.coords_old.x&&!this.coords_old.y) this.diff.set(0,0);
        if(this.isAutoActive&&!this.takeoverActive) this.diff.multiplyScalar(this.autoIntensity); }
    }
    const Mouse=new MouseClass();

    class AutoDriver {
      constructor(mouse,manager,opts){ this.mouse=mouse; this.manager=manager; this.enabled=opts.enabled; this.speed=opts.speed;
        this.resumeDelay=opts.resumeDelay||3000; this.rampDurationMs=(opts.rampDuration||0)*1000; this.active=false;
        this.current=new THREE.Vector2(); this.target=new THREE.Vector2(); this.lastTime=performance.now(); this.activationTime=0; this.margin=0.2;
        this._d=new THREE.Vector2(); this.pickNewTarget(); }
      pickNewTarget(){ const r=Math.random; this.target.set((r()*2-1)*(1-this.margin),(r()*2-1)*(1-this.margin)); }
      forceStop(){ this.active=false; this.mouse.isAutoActive=false; }
      update(){ if(!this.enabled) return; const now=performance.now(),idle=now-this.manager.lastUserInteraction;
        if(idle<this.resumeDelay||this.mouse.isHoverInside){ if(this.active) this.forceStop(); return; }
        if(!this.active){ this.active=true; this.current.copy(this.mouse.coords); this.lastTime=now; this.activationTime=now; }
        this.mouse.isAutoActive=true;
        let ds=(now-this.lastTime)/1000; this.lastTime=now; if(ds>0.2) ds=0.016;
        const dir=this._d.subVectors(this.target,this.current),dist=dir.length();
        if(dist<0.01){ this.pickNewTarget(); return; } dir.normalize();
        let ramp=1; if(this.rampDurationMs>0){ const t=Math.min(1,(now-this.activationTime)/this.rampDurationMs); ramp=t*t*(3-2*t); }
        this.current.addScaledVector(dir,Math.min(this.speed*ds*ramp,dist)); this.mouse.setNormalized(this.current.x,this.current.y); }
    }

    // GLSL (minified single-line strings to keep file smaller)
    const fv=`attribute vec3 position;uniform vec2 px;uniform vec2 boundarySpace;varying vec2 uv;precision highp float;void main(){vec3 pos=position;vec2 scale=1.0-boundarySpace*2.0;pos.xy=pos.xy*scale;uv=vec2(0.5)+(pos.xy)*0.5;gl_Position=vec4(pos,1.0);}`;
    const lv=`attribute vec3 position;uniform vec2 px;precision highp float;varying vec2 uv;void main(){vec3 pos=position;uv=0.5+pos.xy*0.5;vec2 n=sign(pos.xy);pos.xy=abs(pos.xy)-px*1.0;pos.xy*=n;gl_Position=vec4(pos,1.0);}`;
    const mv=`precision highp float;attribute vec3 position;attribute vec2 uv;uniform vec2 center;uniform vec2 scale;uniform vec2 px;varying vec2 vUv;void main(){vec2 pos=position.xy*scale*2.0*px+center;vUv=uv;gl_Position=vec4(pos,0.0,1.0);}`;
    const af=`precision highp float;uniform sampler2D velocity;uniform float dt;uniform bool isBFECC;uniform vec2 fboSize;uniform vec2 px;varying vec2 uv;void main(){vec2 ratio=max(fboSize.x,fboSize.y)/fboSize;if(!isBFECC){vec2 vel=texture2D(velocity,uv).xy;gl_FragColor=vec4(texture2D(velocity,uv-vel*dt*ratio).xy,0,0);}else{vec2 sn=uv,vo=texture2D(velocity,uv).xy,so=sn-vo*dt*ratio,vn1=texture2D(velocity,so).xy,sn2=so+vn1*dt*ratio,err=sn2-sn,sn3=sn-err/2.0,v2=texture2D(velocity,sn3).xy,so2=sn3-v2*dt*ratio;gl_FragColor=vec4(texture2D(velocity,so2).xy,0,0);}}`;
    const cf=`precision highp float;uniform sampler2D velocity;uniform sampler2D palette;uniform vec4 bgColor;varying vec2 uv;void main(){vec2 vel=texture2D(velocity,uv).xy;float l=clamp(length(vel),0.0,1.0);vec3 c=texture2D(palette,vec2(l,0.5)).rgb;gl_FragColor=vec4(mix(bgColor.rgb,c,l),mix(bgColor.a,1.0,l));}`;
    const df=`precision highp float;uniform sampler2D velocity;uniform float dt;uniform vec2 px;varying vec2 uv;void main(){float x0=texture2D(velocity,uv-vec2(px.x,0)).x,x1=texture2D(velocity,uv+vec2(px.x,0)).x,y0=texture2D(velocity,uv-vec2(0,px.y)).y,y1=texture2D(velocity,uv+vec2(0,px.y)).y;gl_FragColor=vec4((x1-x0+y1-y0)/2.0/dt);}`;
    const ef=`precision highp float;uniform vec2 force;uniform vec2 center;uniform vec2 scale;uniform vec2 px;varying vec2 vUv;void main(){vec2 c=(vUv-0.5)*2.0;float d=1.0-min(length(c),1.0);d*=d;gl_FragColor=vec4(force*d,0,1);}`;
    const pf=`precision highp float;uniform sampler2D pressure;uniform sampler2D divergence;uniform vec2 px;varying vec2 uv;void main(){float p0=texture2D(pressure,uv+vec2(px.x*2,0)).r,p1=texture2D(pressure,uv-vec2(px.x*2,0)).r,p2=texture2D(pressure,uv+vec2(0,px.y*2)).r,p3=texture2D(pressure,uv-vec2(0,px.y*2)).r,div=texture2D(divergence,uv).r;gl_FragColor=vec4((p0+p1+p2+p3)/4.0-div);}`;
    const prf=`precision highp float;uniform sampler2D pressure;uniform sampler2D velocity;uniform vec2 px;uniform float dt;varying vec2 uv;void main(){float p0=texture2D(pressure,uv+vec2(px.x,0)).r,p1=texture2D(pressure,uv-vec2(px.x,0)).r,p2=texture2D(pressure,uv+vec2(0,px.y)).r,p3=texture2D(pressure,uv-vec2(0,px.y)).r;vec2 v=texture2D(velocity,uv).xy-vec2(p0-p1,p2-p3)*0.5*dt;gl_FragColor=vec4(v,0,1);}`;
    const vf=`precision highp float;uniform sampler2D velocity;uniform sampler2D velocity_new;uniform float v;uniform vec2 px;uniform float dt;varying vec2 uv;void main(){vec2 old=texture2D(velocity,uv).xy,n0=texture2D(velocity_new,uv+vec2(px.x*2,0)).xy,n1=texture2D(velocity_new,uv-vec2(px.x*2,0)).xy,n2=texture2D(velocity_new,uv+vec2(0,px.y*2)).xy,n3=texture2D(velocity_new,uv-vec2(0,px.y*2)).xy;vec2 nv=4.0*old+v*dt*(n0+n1+n2+n3);nv/=4.0*(1.0+v*dt);gl_FragColor=vec4(nv,0,0);}`;

    class SP {
      constructor(p){ this.props=p||{}; this.uniforms=p?.material?.uniforms; this.scene=this.camera=this.material=this.geometry=this.plane=null; }
      init(){ this.scene=new THREE.Scene(); this.camera=new THREE.Camera();
        if(this.uniforms){ this.material=new THREE.RawShaderMaterial(this.props.material);
          this.geometry=new THREE.PlaneGeometry(2,2); this.plane=new THREE.Mesh(this.geometry,this.material); this.scene.add(this.plane); } }
      update(){ Common.renderer.setRenderTarget(this.props.output||null); Common.renderer.render(this.scene,this.camera); Common.renderer.setRenderTarget(null); }
    }
    class Advection extends SP {
      constructor(p){ super({material:{vertexShader:fv,fragmentShader:af,uniforms:{boundarySpace:{value:p.cellScale},px:{value:p.cellScale},fboSize:{value:p.fboSize},velocity:{value:p.src.texture},dt:{value:p.dt},isBFECC:{value:true}}},output:p.dst});
        this.uniforms=this.props.material.uniforms; this.init(); }
      init(){ super.init(); const g=new THREE.BufferGeometry();
        g.setAttribute('position',new THREE.BufferAttribute(new Float32Array([-1,-1,0,-1,1,0,-1,1,0,1,1,0,1,1,0,1,-1,0,1,-1,0,-1,-1,0]),3));
        this.line=new THREE.LineSegments(g,new THREE.RawShaderMaterial({vertexShader:lv,fragmentShader:af,uniforms:this.uniforms})); this.scene.add(this.line); }
      update({dt,isBounce,BFECC}){ this.uniforms.dt.value=dt; this.line.visible=isBounce; this.uniforms.isBFECC.value=BFECC; super.update(); }
    }
    class ExternalForce extends SP {
      constructor(p){ super({output:p.dst}); super.init();
        const m=new THREE.RawShaderMaterial({vertexShader:mv,fragmentShader:ef,blending:THREE.AdditiveBlending,depthWrite:false,
          uniforms:{px:{value:p.cellScale},force:{value:new THREE.Vector2()},center:{value:new THREE.Vector2()},scale:{value:new THREE.Vector2(p.cursor_size,p.cursor_size)}}});
        this.mouse=new THREE.Mesh(new THREE.PlaneGeometry(1,1),m); this.scene.add(this.mouse); }
      update(p){ const fx=(Mouse.diff.x/2)*p.mouse_force,fy=(Mouse.diff.y/2)*p.mouse_force,cx=p.cursor_size*p.cellScale.x,cy=p.cursor_size*p.cellScale.y,u=this.mouse.material.uniforms;
        u.force.value.set(fx,fy); u.center.value.set(Math.min(Math.max(Mouse.coords.x,-1+cx+p.cellScale.x*2),1-cx-p.cellScale.x*2),Math.min(Math.max(Mouse.coords.y,-1+cy+p.cellScale.y*2),1-cy-p.cellScale.y*2)); u.scale.value.set(p.cursor_size,p.cursor_size); super.update(); }
    }
    class Viscous extends SP {
      constructor(p){ super({material:{vertexShader:fv,fragmentShader:vf,uniforms:{boundarySpace:{value:p.boundarySpace},velocity:{value:p.src.texture},velocity_new:{value:p.dst_.texture},v:{value:p.viscous},px:{value:p.cellScale},dt:{value:p.dt}}},output:p.dst,output0:p.dst_,output1:p.dst}); this.init(); }
      update({viscous,iterations,dt}){ let fi,fo; this.uniforms.v.value=viscous;
        for(let i=0;i<iterations;i++){ fi=i%2===0?this.props.output0:this.props.output1; fo=i%2===0?this.props.output1:this.props.output0;
          this.uniforms.velocity_new.value=fi.texture; this.props.output=fo; this.uniforms.dt.value=dt; super.update(); } return fo; }
    }
    class Divergence extends SP {
      constructor(p){ super({material:{vertexShader:fv,fragmentShader:df,uniforms:{boundarySpace:{value:p.boundarySpace},velocity:{value:p.src.texture},px:{value:p.cellScale},dt:{value:p.dt}}},output:p.dst}); this.init(); }
      update({vel}){ this.uniforms.velocity.value=vel.texture; super.update(); }
    }
    class Poisson extends SP {
      constructor(p){ super({material:{vertexShader:fv,fragmentShader:pf,uniforms:{boundarySpace:{value:p.boundarySpace},pressure:{value:p.dst_.texture},divergence:{value:p.src.texture},px:{value:p.cellScale}}},output:p.dst,output0:p.dst_,output1:p.dst}); this.init(); }
      update({iterations}){ let pi,po;
        for(let i=0;i<iterations;i++){ pi=i%2===0?this.props.output0:this.props.output1; po=i%2===0?this.props.output1:this.props.output0; this.uniforms.pressure.value=pi.texture; this.props.output=po; super.update(); } return po; }
    }
    class Pressure extends SP {
      constructor(p){ super({material:{vertexShader:fv,fragmentShader:prf,uniforms:{boundarySpace:{value:p.boundarySpace},pressure:{value:p.src_p.texture},velocity:{value:p.src_v.texture},px:{value:p.cellScale},dt:{value:p.dt}}},output:p.dst}); this.init(); }
      update({vel,pressure}){ this.uniforms.velocity.value=vel.texture; this.uniforms.pressure.value=pressure.texture; super.update(); }
    }

    class Simulation {
      constructor(opts={}){
        this.options={iterations_poisson:32,iterations_viscous:32,mouse_force:20,resolution:0.5,cursor_size:100,viscous:30,isBounce:false,dt:0.014,isViscous:false,BFECC:true,...opts};
        this.fbos={vel_0:null,vel_1:null,vel_viscous0:null,vel_viscous1:null,div:null,pressure_0:null,pressure_1:null};
        this.fboSize=new THREE.Vector2(); this.cellScale=new THREE.Vector2(); this.boundarySpace=new THREE.Vector2(); this.init(); }
      init(){ this.calcSize(); this.createAllFBO(); this.createShaderPass(); }
      getFloatType(){ return /(iPad|iPhone|iPod)/i.test(navigator.userAgent)?THREE.HalfFloatType:THREE.FloatType; }
      createAllFBO(){ const o={type:this.getFloatType(),depthBuffer:false,stencilBuffer:false,minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,wrapS:THREE.ClampToEdgeWrapping,wrapT:THREE.ClampToEdgeWrapping};
        for(const k in this.fbos) this.fbos[k]=new THREE.WebGLRenderTarget(this.fboSize.x,this.fboSize.y,o); }
      createShaderPass(){ const{options:o,fbos:f,cellScale:cs,boundarySpace:bs}=this;
        this.advection=new Advection({cellScale:cs,fboSize:this.fboSize,dt:o.dt,src:f.vel_0,dst:f.vel_1});
        this.externalForce=new ExternalForce({cellScale:cs,cursor_size:o.cursor_size,dst:f.vel_1});
        this.viscous=new Viscous({cellScale:cs,boundarySpace:bs,viscous:o.viscous,src:f.vel_1,dst:f.vel_viscous1,dst_:f.vel_viscous0,dt:o.dt});
        this.divergence=new Divergence({cellScale:cs,boundarySpace:bs,src:f.vel_viscous0,dst:f.div,dt:o.dt});
        this.poisson=new Poisson({cellScale:cs,boundarySpace:bs,src:f.div,dst:f.pressure_1,dst_:f.pressure_0});
        this.pressure=new Pressure({cellScale:cs,boundarySpace:bs,src_p:f.pressure_0,src_v:f.vel_viscous0,dst:f.vel_0,dt:o.dt}); }
      calcSize(){ const w=Math.max(1,Math.round(this.options.resolution*Common.width)),h=Math.max(1,Math.round(this.options.resolution*Common.height));
        this.cellScale.set(1/w,1/h); this.fboSize.set(w,h); }
      resize(){ this.calcSize(); for(const k in this.fbos) this.fbos[k].setSize(this.fboSize.x,this.fboSize.y); }
      update(){ const o=this.options; this.boundarySpace.copy(o.isBounce?new THREE.Vector2():this.cellScale);
        this.advection.update({dt:o.dt,isBounce:o.isBounce,BFECC:o.BFECC});
        this.externalForce.update({cursor_size:o.cursor_size,mouse_force:o.mouse_force,cellScale:this.cellScale});
        let vel=this.fbos.vel_1;
        if(o.isViscous) vel=this.viscous.update({viscous:o.viscous,iterations:o.iterations_viscous,dt:o.dt});
        this.divergence.update({vel}); const pressure=this.poisson.update({iterations:o.iterations_poisson}); this.pressure.update({vel,pressure}); }
    }

    class Output {
      constructor(){ this.simulation=new Simulation(); this.scene=new THREE.Scene(); this.camera=new THREE.Camera();
        this.output=new THREE.Mesh(new THREE.PlaneGeometry(2,2),new THREE.RawShaderMaterial({vertexShader:fv,fragmentShader:cf,transparent:true,depthWrite:false,
          uniforms:{velocity:{value:this.simulation.fbos.vel_0.texture},boundarySpace:{value:new THREE.Vector2()},palette:{value:paletteTex},bgColor:{value:bgVec4}}}));
        this.scene.add(this.output); }
      resize(){ this.simulation.resize(); }
      render(){ Common.renderer.setRenderTarget(null); Common.renderer.render(this.scene,this.camera); }
      update(){ this.simulation.update(); this.render(); }
    }

    class WebGLManager {
      constructor(p){ this.props=p; Common.init(p.$wrapper); Mouse.init(p.$wrapper);
        Mouse.autoIntensity=p.autoIntensity; Mouse.takeoverDuration=p.takeoverDuration;
        this.lastUserInteraction=performance.now();
        Mouse.onInteract=()=>{ this.lastUserInteraction=performance.now(); this.autoDriver?.forceStop(); };
        this.autoDriver=new AutoDriver(Mouse,this,{enabled:p.autoDemo,speed:p.autoSpeed,resumeDelay:p.autoResumeDelay,rampDuration:p.autoRampDuration});
        p.$wrapper.prepend(Common.renderer.domElement); this.output=new Output();
        this._loop=this.loop.bind(this); this._resize=this.resize.bind(this);
        window.addEventListener('resize',this._resize);
        this._onVis=()=>{ if(document.hidden) this.pause(); else if(isVisibleRef.current) this.start(); };
        document.addEventListener('visibilitychange',this._onVis); this.running=false; }
      resize(){ Common.resize(); this.output.resize(); }
      render(){ this.autoDriver?.update(); Mouse.update(); Common.update(); this.output.update(); }
      loop(){ if(!this.running) return; this.render(); rafRef.current=requestAnimationFrame(this._loop); }
      start(){ if(this.running) return; this.running=true; this._loop(); }
      pause(){ this.running=false; if(rafRef.current){ cancelAnimationFrame(rafRef.current); rafRef.current=null; } }
      dispose(){ try{ window.removeEventListener('resize',this._resize); document.removeEventListener('visibilitychange',this._onVis); Mouse.dispose();
          if(Common.renderer){ const c=Common.renderer.domElement; if(c?.parentNode) c.parentNode.removeChild(c); Common.renderer.dispose(); Common.renderer.forceContextLoss(); }
        }catch(e){ void 0; } }
    }

    const container=mountRef.current;
    container.style.position=container.style.position||'relative';
    container.style.overflow=container.style.overflow||'hidden';
    const webgl=new WebGLManager({$wrapper:container,autoDemo,autoSpeed,autoIntensity,takeoverDuration,autoResumeDelay,autoRampDuration});
    webglRef.current=webgl;
    const sim=webgl.output?.simulation;
    if(sim) Object.assign(sim.options,{mouse_force:mouseForce,cursor_size:cursorSize,isViscous,viscous,iterations_viscous:iterationsViscous,iterations_poisson:iterationsPoisson,dt,BFECC,resolution,isBounce});
    webgl.start();

    const io=new IntersectionObserver(entries=>{ const v=entries[0].isIntersecting&&entries[0].intersectionRatio>0; isVisibleRef.current=v;
      if(!webglRef.current) return; v&&!document.hidden?webglRef.current.start():webglRef.current.pause(); },{threshold:[0,0.01,0.1]});
    io.observe(container); intersectionObserverRef.current=io;

    const ro=new ResizeObserver(()=>{ if(!webglRef.current) return;
      if(resizeRafRef.current) cancelAnimationFrame(resizeRafRef.current);
      resizeRafRef.current=requestAnimationFrame(()=>{ if(webglRef.current) webglRef.current.resize(); }); });
    ro.observe(container); resizeObserverRef.current=ro;

    return ()=>{ if(rafRef.current) cancelAnimationFrame(rafRef.current);
      try{ resizeObserverRef.current?.disconnect(); }catch(e){ void 0; }
      try{ intersectionObserverRef.current?.disconnect(); }catch(e){ void 0; }
      if(webglRef.current){ webglRef.current.dispose(); webglRef.current=null; } };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[BFECC,cursorSize,dt,isBounce,isViscous,iterationsPoisson,iterationsViscous,mouseForce,resolution,viscous,colors,autoDemo,autoSpeed,autoIntensity,takeoverDuration,autoResumeDelay,autoRampDuration]);

  useEffect(()=>{
    const webgl=webglRef.current; if(!webgl) return; const sim=webgl.output?.simulation; if(!sim) return;
    const prevRes=sim.options.resolution;
    Object.assign(sim.options,{mouse_force:mouseForce,cursor_size:cursorSize,isViscous,viscous,iterations_viscous:iterationsViscous,iterations_poisson:iterationsPoisson,dt,BFECC,resolution,isBounce});
    if(webgl.autoDriver){ webgl.autoDriver.enabled=autoDemo; webgl.autoDriver.speed=autoSpeed; webgl.autoDriver.resumeDelay=autoResumeDelay; webgl.autoDriver.rampDurationMs=autoRampDuration*1000;
      if(webgl.autoDriver.mouse){ webgl.autoDriver.mouse.autoIntensity=autoIntensity; webgl.autoDriver.mouse.takeoverDuration=takeoverDuration; } }
    if(resolution!==prevRes) sim.resize();
  },[mouseForce,cursorSize,isViscous,viscous,iterationsViscous,iterationsPoisson,dt,BFECC,resolution,isBounce,autoDemo,autoSpeed,autoIntensity,takeoverDuration,autoResumeDelay,autoRampDuration]);

  return <div ref={mountRef} className={`liquid-ether-container${className?' '+className:''}`} style={style}/>;
}
