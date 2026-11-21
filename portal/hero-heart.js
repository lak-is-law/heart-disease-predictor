/* CardioSense hero: an anatomical heart (four chambers, both atrial appendages, aorta with arch
   branches, pulmonary trunk and arteries, venae cavae) drawn in one WebGL fragment shader.
   Scrolling through the hero turns the heart and opens it along the four-chamber plane.
   No libraries and no model files. */
(function () {
  'use strict';
  var canvas = document.getElementById('hx-canvas');
  var hero = document.getElementById('hero-overview');
  if (!canvas || !hero) return;

  // Copy beats cross-fade with scroll. This works with or without WebGL.
  var beats = hero.querySelectorAll('.hx-copy'), beatNow = -1;
  function heroProgress() {
    var r = hero.getBoundingClientRect(), span = hero.offsetHeight - window.innerHeight;
    return span > 0 ? Math.min(Math.max(-r.top / span, 0), 1) : 0;
  }
  function updateBeats() {
    var p = heroProgress(), b = p < 0.22 ? 0 : (p < 0.82 ? 1 : 2);
    if (b === beatNow) return;
    beatNow = b;
    for (var i = 0; i < beats.length; i++) {
      beats[i].classList.toggle('is-on', +beats[i].getAttribute('data-beat') === b);
    }
  }
  window.addEventListener('scroll', updateBeats, { passive: true });
  window.addEventListener('resize', updateBeats);
  updateBeats();

  var gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false });
  if (!gl) { canvas.hidden = true; return; }

  var VERT = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';

  var FRAG = [
    'precision highp float;',
    'uniform vec2 uRes;uniform float uRot,uTilt,uCut,uScale;',

    'float smin(float a,float b,float k){float h=clamp(.5+.5*(b-a)/k,0.,1.);return mix(b,a,h)-k*h*(1.-h);}',
    // ellipsoid, rotated about z
    'float sdEll(vec3 p,vec3 c,vec3 r,float a){p-=c;float s=sin(a),co=cos(a);p.xy=vec2(co*p.x+s*p.y,-s*p.x+co*p.y);',
    '  float k0=length(p/r),k1=length(p/(r*r));return k0*(k0-1.)/max(k1,1e-4);}',
    'float sdCap(vec3 p,vec3 a,vec3 b,float r){vec3 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h)-r;}',

    // atria, ventricles and the two atrial appendages
    'float chambers(vec3 p){',
    '  float lv=sdEll(p,vec3(.28,-.30,-.02),vec3(.62,1.05,.55),.42);',
    '  float rv=sdEll(p,vec3(-.30,-.28,.30),vec3(.48,.92,.40),.40);',
    '  float la=sdEll(p,vec3(.42,.52,-.42),vec3(.46,.30,.38),0.);',
    '  float ra=sdEll(p,vec3(-.64,.30,-.05),vec3(.34,.50,.38),.10);',
    '  float laa=sdEll(p,vec3(.30,.78,.10),vec3(.20,.16,.14),.5);',
    '  float raa=sdEll(p,vec3(-.52,.72,.22),vec3(.24,.20,.18),-.3);',
    '  float d=smin(lv,rv,.16);d=smin(d,la,.14);d=smin(d,ra,.14);d=smin(d,laa,.08);return smin(d,raa,.10);}',

    // aorta with its three arch branches, and the pulmonary veins (oxygenated, drawn red)
    'float redVessels(vec3 p){',
    '  float d=sdCap(p,vec3(.05,.50,.05),vec3(.10,1.15,-.02),.21);',
    '  d=smin(d,sdCap(p,vec3(.10,1.15,-.02),vec3(.45,1.42,-.20),.20),.08);',
    '  d=smin(d,sdCap(p,vec3(.45,1.42,-.20),vec3(.80,1.20,-.36),.19),.08);',
    '  d=smin(d,sdCap(p,vec3(.80,1.20,-.36),vec3(.82,.30,-.50),.19),.08);',
    '  d=min(d,sdCap(p,vec3(.22,1.30,-.10),vec3(.18,1.85,-.12),.085));',
    '  d=min(d,sdCap(p,vec3(.42,1.40,-.20),vec3(.45,1.85,-.22),.07));',
    '  d=min(d,sdCap(p,vec3(.62,1.36,-.28),vec3(.85,1.75,-.30),.075));',
    '  d=min(d,sdCap(p,vec3(.80,.55,-.45),vec3(1.15,.75,-.45),.09));',
    '  return min(d,sdCap(p,vec3(.80,.40,-.45),vec3(1.15,.25,-.45),.09));}',

    // pulmonary trunk and arteries, venae cavae (deoxygenated, drawn blue)
    'float blueVessels(vec3 p){',
    '  float d=sdCap(p,vec3(-.08,.50,.38),vec3(.05,1.02,.22),.20);',
    '  d=smin(d,sdCap(p,vec3(.05,1.02,.22),vec3(.72,1.05,-.05),.13),.06);',
    '  d=smin(d,sdCap(p,vec3(.05,1.02,.22),vec3(-.55,1.05,-.30),.12),.06);',
    '  d=min(d,sdCap(p,vec3(-.70,.55,-.05),vec3(-.68,1.55,-.10),.14));',
    '  return min(d,sdCap(p,vec3(-.58,-.05,-.12),vec3(-.58,-.75,-.14),.15));}',

    // coronary arteries (LAD down the front groove, RCA around the right AV groove), laid on the surface
    'float poly(vec3 p,vec3 a,vec3 b,vec3 c,vec3 d,vec3 e,vec3 f){',
    '  return min(min(min(sdCap(p,a,b,0.),sdCap(p,b,c,0.)),min(sdCap(p,c,d,0.),sdCap(p,d,e,0.))),sdCap(p,e,f,0.));}',
    'float coronary(vec3 p){',
    '  float lad=poly(p,vec3(.16,.46,.331),vec3(.12,.26,.433),vec3(.12,0.,.513),vec3(.18,-.34,.553),vec3(.27,-.72,.492),vec3(.37,-1.08,.303));',
    '  float rca=poly(p,vec3(-.02,.46,.566),vec3(-.26,.44,.472),vec3(-.52,.34,.577),vec3(-.76,.10,.533),vec3(-.80,-.26,.396),vec3(-.66,-.62,.368));',
    '  return min(lad,rca);}',
    'float outer(vec3 p){return smin(smin(chambers(p),redVessels(p),.08),blueVessels(p),.08);}',

    // blood-filled spaces: four chambers, mitral and tricuspid openings, outflow tracts
    'float cavities(vec3 p){',
    '  float d=min(sdEll(p,vec3(.40,-.28,-.02),vec3(.34,.80,.34),.42),sdEll(p,vec3(-.40,-.26,.30),vec3(.26,.68,.26),.40));',
    '  d=min(d,sdEll(p,vec3(.42,.52,-.42),vec3(.36,.26,.30),0.));',
    '  d=min(d,sdEll(p,vec3(-.64,.30,-.05),vec3(.22,.38,.26),.10));',
    '  d=min(d,sdCap(p,vec3(.40,.50,-.30),vec3(.40,.10,-.12),.15));',
    '  d=min(d,sdCap(p,vec3(-.55,.20,.05),vec3(-.45,-.10,.22),.12));',
    '  d=min(d,sdCap(p,vec3(.20,.10,.02),vec3(.10,1.15,-.02),.15));',
    '  d=min(d,sdCap(p,vec3(.10,1.15,-.02),vec3(.45,1.42,-.20),.14));',
    '  d=min(d,sdCap(p,vec3(.45,1.42,-.20),vec3(.80,1.20,-.36),.13));',
    '  d=min(d,sdCap(p,vec3(.80,1.20,-.36),vec3(.82,.35,-.50),.13));',
    '  d=min(d,sdCap(p,vec3(-.25,.15,.32),vec3(-.08,.50,.38),.12));',
    '  d=min(d,sdCap(p,vec3(-.08,.50,.38),vec3(.05,1.02,.22),.13));',
    '  return min(d,sdCap(p,vec3(-.70,.55,-.05),vec3(-.68,1.55,-.10),.08));}',

    // the four-chamber plane: removes everything in front of it
    'float cutPlane(vec3 p){return dot(p,vec3(.34,.43,.84))-uCut;}',
    'float map(vec3 p){return max(max(outer(p),-cavities(p)),cutPlane(p));}',
    'vec3 nrm(vec3 p){vec2 e=vec2(.003,-.003);return normalize(e.xyy*map(p+e.xyy)+e.yyx*map(p+e.yyx)+e.yxy*map(p+e.yxy)+e.xxx*map(p+e.xxx));}',

    // cheap value noise for tissue texture
    'float h3(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}',
    'float vn(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);',
    '  return mix(mix(mix(h3(i),h3(i+vec3(1,0,0)),f.x),mix(h3(i+vec3(0,1,0)),h3(i+vec3(1,1,0)),f.x),f.y),',
    '             mix(mix(h3(i+vec3(0,0,1)),h3(i+vec3(1,0,1)),f.x),mix(h3(i+vec3(0,1,1)),h3(i+vec3(1,1,1)),f.x),f.y),f.z);}',

    'vec3 env(vec3 d){',
    '  float h=d.y*.5+.5;',
    '  vec3 c=mix(vec3(.015,.025,.05),vec3(.10,.15,.24),smoothstep(0.,.7,h));',
    '  c+=vec3(1.,.95,.9)*2.2*smoothstep(.93,.985,dot(d,normalize(vec3(-.5,.8,.6))));',
    '  c+=vec3(.0,.9,1.)*1.4*smoothstep(.90,.97,dot(d,normalize(vec3(.9,.2,-.5))));',
    '  return c;}',

    'void main(){',
    '  vec2 uv=(gl_FragCoord.xy-.5*uRes)/uRes.y;uv/=uScale;',
    '  vec3 ro=vec3(0.,0.,6.2),rd=normalize(vec3(uv,-1.8));',
    '  float cr=cos(uRot),sr=sin(uRot),ct=cos(uTilt),st=sin(uTilt);',
    '  mat3 R=mat3(cr,0.,-sr,0.,1.,0.,sr,0.,cr)*mat3(1.,0.,0.,0.,ct,st,0.,-st,ct);',
    '  vec3 C=vec3(.10,.30,0.);',
    '  vec3 o=ro*R+C,d=rd*R;',
    '  vec3 oc=o-C;float b=dot(oc,d),c=dot(oc,oc)-2.2*2.2,h=b*b-c;',
    '  if(h<0.){gl_FragColor=vec4(0.);return;}',
    '  float t=-b-sqrt(h),tmax=-b+sqrt(h);',
    '  float md=1e9,tm=t;bool hit=false;',
    '  for(int i=0;i<96;i++){',
    '    float s=map(o+d*t);',
    '    if(s<md){md=s;tm=t;}',
    '    if(s<.0015){hit=true;tm=t;break;}',
    '    t+=max(s*.7,.004);',
    '    if(t>tmax)break;}',
    '  float px=3.4/(uRes.y*uScale);',
    '  float a=hit?1.:1.-smoothstep(0.,px*1.5,md);',
    '  if(a<=0.){gl_FragColor=vec4(0.);return;}',
    '  vec3 p=o+d*tm;',
    '  vec3 n=nrm(p);',
    // which surface did we reach: outside, a chamber lining, or the cut face
    '  float dO=outer(p),dC=-cavities(p),dP=cutPlane(p);',
    '  bool isCut=dP>=max(dO,dC)-.004,isLining=!isCut&&dC>dO;',
    // tissue texture: fine grain on the normal
    '  vec3 q=p*22.;',
    '  n=normalize(n+.10*vec3(vn(q)-.5,vn(q+7.3)-.5,vn(q+13.1)-.5));',
    '  vec3 nw=R*n,v=normalize(-rd);',
    '  float ndv=clamp(dot(nw,v),0.,1.);',
    '  float ao=1.;for(int i=1;i<=3;i++){float hh=.07*float(i);ao-=(hh-map(p+n*hh))*.5/float(i);}ao=clamp(ao,0.,1.);',
    // colour by region
    '  float dCh=chambers(p),dR=redVessels(p),dB=blueVessels(p);',
    '  float wR=smoothstep(.02,-.02,dR-min(dCh,dB)),wB=smoothstep(.02,-.02,dB-min(dCh,dR));',
    '  float mott=.85+.3*vn(p*7.);',
    '  vec3 col=mix(vec3(.38,.045,.075),vec3(.52,.09,.10),wR);col=mix(col,vec3(.12,.27,.52),wB);col*=mott;',
    '  float cd=coronary(p);',
    '  col=mix(col,vec3(.78,.60,.28)*mott,smoothstep(.11,.035,cd)*.55);',   // epicardial fat beside the artery
    '  col=mix(col,vec3(.28,.015,.035),smoothstep(.026,.012,cd));',
    '  float spec=.55,gloss=70.;',
    '  if(isLining){',
    '    float right=smoothstep(-.05,.05,-(p.x+.05)+.15*p.z);',   // right-sided chambers read cooler
    '    col=mix(vec3(.62,.18,.22),vec3(.46,.26,.40),right)*(.9+.2*vn(p*11.));spec=.8;gloss=90.;}',
    '  if(isCut){',
    '    col=vec3(.50,.085,.10)*(.78+.44*vn(p*30.+vec3(0.,p.y*40.,0.)));',  // muscle fibres in section
    '    spec=.12;gloss=20.;}',
    '  vec3 L1=normalize(vec3(-.5,.8,.6)),L2=normalize(vec3(.9,.2,-.5)),L3=normalize(vec3(-.3,-.7,.5));',
    '  vec3 hv1=normalize(L1+v),hv2=normalize(L2+v);',
    '  float d1=clamp(dot(nw,L1)*.5+.5,0.,1.);',
    '  vec3 lit=col*(.10+.95*d1*d1)*vec3(1.,.94,.9);',
    '  lit+=col*vec3(.0,.55,.7)*pow(clamp(dot(nw,L2)*.5+.5,0.,1.),3.)*.55;',     // cyan rim from the favicon palette
    '  lit+=col*vec3(.1,.18,.4)*clamp(dot(nw,L3)*.5+.5,0.,1.)*.25;',
    '  lit+=vec3(1.,.95,.9)*pow(max(dot(nw,hv1),0.),gloss)*spec;',
    '  lit+=vec3(.0,.9,1.)*pow(max(dot(nw,hv2),0.),gloss*.6)*spec*.7;',
    '  float fr=.03+.97*pow(1.-ndv,4.);',
    '  lit+=env(reflect(-v,nw))*fr*(isCut?.25:.9);',
    '  lit*=mix(.35,1.,ao);',
    '  lit=lit/(1.+lit*.25);lit=pow(lit,vec3(1./2.2));',
    '  gl_FragColor=vec4(lit*a,a);',
    '}'
  ].join('\n');

  function compile(type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error(gl.getShaderInfoLog(s)); return null; }
    return s;
  }
  var vs = compile(gl.VERTEX_SHADER, VERT), fs = compile(gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) { canvas.hidden = true; return; }
  var prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog); gl.useProgram(prog);
  var buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  var loc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  var U = {};
  ['uRes', 'uRot', 'uTilt', 'uCut', 'uScale'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var res = 1, w = 0, h = 0, slow = 0, visible = true, last = performance.now();
  var cur = { rot: 0.5, cut: 3, y: 0 }, tgt = { rot: 0.5, cut: 3, y: 0 };
  var debug = window.__heartDebug || null;

  // Scroll progress through the hero (0 at the top, 1 when the hero scrolls away).
  // The heart turns, opens along the four-chamber plane, then closes again.
  var ease = function (k) { return k * k * (3 - 2 * k); };
  function keys(p) {
    var TAU = Math.PI * 2, rot, cut, k;
    if (p < 0.25) { rot = 0.5 + p * 1.6; cut = 3; }                                    // slow turn, closed
    else if (p < 0.65) { k = ease((p - 0.25) / 0.40); rot = 0.9 + (TAU - 0.9) * k; cut = 3 - 3 * k; }   // spin face-on while opening
    else if (p < 0.85) { rot = TAU + (p - 0.65) * 0.3; cut = 0; }                      // held open: four chambers visible
    else { k = ease((p - 0.85) / 0.15); rot = TAU + 0.06 + k * 0.9; cut = 3 * k; }      // close again
    return { rot: rot, cut: cut };
  }
  function progress() {
    var r = hero.getBoundingClientRect(), span = hero.offsetHeight - window.innerHeight;
    return span > 0 ? Math.min(Math.max(-r.top / span, 0), 1) : 0;
  }

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5) * res;
    w = Math.max(2, Math.round(canvas.clientWidth * dpr));
    h = Math.max(2, Math.round(canvas.clientHeight * dpr));
    canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h);
  }

  function draw(rot, cut) {
    gl.uniform2f(U.uRes, w, h);
    gl.uniform1f(U.uRot, rot);
    gl.uniform1f(U.uTilt, 0.08);
    gl.uniform1f(U.uCut, cut);
    gl.uniform1f(U.uScale, 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible || document.hidden) return;
    var rect = hero.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) return;   // hero off screen: do no work
    var dt = Math.min((now - last) / 1000, 0.05); last = now;
    var k = keys(progress());
    tgt.rot = k.rot; tgt.cut = k.cut;
    var f = reduce ? 1 : 1 - Math.pow(0.001, dt);
    cur.rot += (tgt.rot - cur.rot) * f; cur.cut += (tgt.cut - cur.cut) * f;
    draw(cur.rot + (reduce ? 0 : Math.sin(now / 4000) * 0.08 * Math.min(cur.cut, 1)), cur.cut);
    slow = slow * 0.95 + dt * 1000 * 0.05;
    if (slow > 28 && res > 0.5) { res -= 0.15; slow = 16; resize(); }   // draw smaller instead of stuttering
  }

  window.addEventListener('resize', resize);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (e) { visible = e[0].isIntersecting; last = performance.now(); }).observe(hero);
  }
  resize();
  if (debug) { draw(debug.rot, debug.cut); canvas.classList.add('ready'); return; }   // used for visual tests
  requestAnimationFrame(function (t) { last = t; frame(t); canvas.classList.add('ready'); });
})();
