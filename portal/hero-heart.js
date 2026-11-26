/* CardioSense hero: an anatomical heart (four chambers, both atrial appendages, aorta with arch
   branches, pulmonary trunk and arteries, venae cavae) drawn in one WebGL fragment shader.
   Scrolling through the hero turns the heart and opens it along the four-chamber plane.
   No libraries and no model files. */
(function () {
  'use strict';
  var canvas = document.getElementById('hx-canvas');
  var hero = document.getElementById('hero-overview');
  if (!canvas || !hero) return;

  var beats = hero.querySelectorAll('.hx-copy');
  var landmarks = hero.querySelector('.hx-landmarks');
  var section = hero.querySelector('.hx-section');
  var stillView = window.matchMedia('(prefers-reduced-motion: reduce), (max-height: 560px)');

  function showBeat(index) {
    beats.forEach(function (beat, i) {
      beat.classList.toggle('is-on', i === index);
      beat.inert = i !== index;
      beat.setAttribute('aria-hidden', String(i !== index));
    });
  }

  function showStill() {
    hero.classList.add('hx-static');
    canvas.style.opacity = 0;
    landmarks.hidden = true;
    section.hidden = false;
    section.style.opacity = 1;
    section.setAttribute('aria-hidden', 'false');
    showBeat(0);
  }
  showStill();

  var gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false });
  if (!gl) return;
  canvas.addEventListener('webglcontextlost', showStill);

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
    '  d=smin(d,sdCap(p,vec3(.05,1.02,.22),mix(vec3(-.15,1.03,.09),vec3(-.55,1.05,-.30),smoothstep(.04,.65,uCut)),.12),.06);',
    '  d=min(d,sdCap(p,vec3(-.70,.55,-.05),vec3(-.68,1.55,-.10),.14));',
    '  return min(d,sdCap(p,vec3(-.58,-.05,-.12),vec3(-.58,-.75,-.14),.15));}',

    // coronary arteries (LAD down the front groove, RCA around the right AV groove), laid on the surface
    'float poly(vec3 p,vec3 a,vec3 b,vec3 c,vec3 d,vec3 e,vec3 f){',
    '  return min(min(min(sdCap(p,a,b,0.),sdCap(p,b,c,0.)),min(sdCap(p,c,d,0.),sdCap(p,d,e,0.))),sdCap(p,e,f,0.));}',
    'float coronary(vec3 p){',
    '  float lad=poly(p,vec3(.16,.46,.331),vec3(.12,.26,.433),vec3(.12,0.,.513),vec3(.18,-.34,.553),vec3(.27,-.72,.492),vec3(.37,-1.08,.303));',
    '  float rca=poly(p,vec3(-.02,.46,.566),vec3(-.26,.44,.472),vec3(-.52,.34,.577),vec3(-.76,.10,.533),vec3(-.80,-.26,.396),vec3(-.66,-.62,.368));',
    '  float diagonal=min(sdCap(p,vec3(.18,-.34,.553),vec3(.40,-.42,.52),.010),sdCap(p,vec3(.40,-.42,.52),vec3(.61,-.63,.43),.006));',
    '  float marginal=min(sdCap(p,vec3(-.52,.34,.577),vec3(-.56,.04,.647),.008),sdCap(p,vec3(-.56,.04,.647),vec3(-.51,-.26,.665),.005));',
    '  return min(min(lad,rca),min(diagonal,marginal)+.013);}',
    'float outer(vec3 p){return smin(smin(chambers(p),redVessels(p),.08),blueVessels(p),.08);}',

    // blood-filled spaces: four chambers, mitral and tricuspid openings, outflow tracts
    'float cavities(vec3 p){',
    '  float d=min(sdEll(p,vec3(.40,-.28,-.02),vec3(.34,.80,.34),.42),sdEll(p,vec3(-.40,-.26,.30),vec3(.26,.68,.26),.40));',
    // Low, irregular muscular ridges confined to the ventricular lining.
    '  float ridges=sin(34.*p.x+9.*p.y+4.*sin(5.*p.y+3.*p.z));',
    '  float crossRidges=sin(28.*p.z-13.*p.y+2.*sin(6.*p.x));',
    '  d+=.032*(1.-smoothstep(-.42,-.06,p.y))*smoothstep(.30,.98,max(ridges,crossRidges));',
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
    // Short valve leaflets and their supporting cords sit within the chamber spaces.
    'float valve(vec3 q){',
    '  float cusp=sdEll(q,vec3(-.075,0.,0.),vec3(.095,.048,.12),-.55);',
    '  cusp=min(cusp,sdEll(q,vec3(.08,.015,0.),vec3(.09,.04,.12),.55));',
    '  float cord=sdCap(q,vec3(-.045,-.024,-.025),vec3(-.07,-.37,-.07),.010);',
    '  cord=min(cord,sdCap(q,vec3(.05,-.01,-.035),vec3(-.07,-.37,-.07),.009));',
    '  return min(cusp,cord);}',
    'float apparatus(vec3 p){return min(valve(p-vec3(.40,.16,-.19)),valve(p-vec3(-.48,.07,.13)));}',
    'float map(vec3 p){float tissue=max(outer(p),-cavities(p));',
    '  if(uCut<1. && p.y<.30 && p.y>-.62){',
    '    tissue=min(tissue,apparatus(p));',
    '    tissue=min(tissue,sdEll(p,vec3(.33,-.36,-.26),vec3(.07,.19,.08),-.04));',
    '    tissue=min(tissue,sdEll(p,vec3(-.55,-.44,.06),vec3(.055,.17,.065),-.04));}',
    '  return max(tissue,cutPlane(p));}',
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
    '  float wR=(1.-smoothstep(-.02,.02,dR-min(dCh,dB))),wB=(1.-smoothstep(-.02,.02,dB-min(dCh,dR)));',
    '  float mott=.85+.3*vn(p*7.);',
    '  vec3 col=mix(vec3(.38,.045,.075),vec3(.52,.09,.10),wR);col=mix(col,vec3(.12,.27,.52),wB);col*=mott;',
    '  float cd=coronary(p);',
    '  col=mix(col,vec3(.69,.43,.21)*mott,(1.-smoothstep(.035,.11,cd))*.55);',   // epicardial fat beside the artery
    '  col=mix(col,vec3(.28,.015,.035),(1.-smoothstep(.012,.026,cd)));',
    '  float spec=.24,gloss=44.;',
    '  if(isLining){',
    '    float right=smoothstep(-.05,.05,-(p.x+.05)+.15*p.z);',   // right-sided chambers read cooler
    '    col=mix(vec3(.62,.18,.22),vec3(.46,.26,.40),right)*(.9+.2*vn(p*11.));spec=.22;gloss=48.;}',
    '  if(isCut){',
    '    float fiber=sin(145.*p.y+63.*p.x+8.*sin(4.*p.x)+3.*vn(p*9.)); col=vec3(.50,.095,.105)*(.90+.10*fiber+.16*(vn(p*38.)-.5));',  // muscle fibres in section
    '    spec=.12;gloss=20.;}',
    '  if(uCut<1. && abs(apparatus(p))<.005){col=vec3(.70,.49,.35);spec=.18;}',
    '  vec3 L1=normalize(vec3(-.5,.8,.6)),L2=normalize(vec3(.9,.2,-.5)),L3=normalize(vec3(-.3,-.7,.5));',
    '  vec3 hv1=normalize(L1+v),hv2=normalize(L2+v);',
    '  float d1=clamp(dot(nw,L1)*.5+.5,0.,1.);',
    '  vec3 lit=col*(.10+.95*d1*d1)*vec3(1.,.94,.9);',
    '  lit+=col*vec3(.45,.5,.6)*pow(clamp(dot(nw,L2)*.5+.5,0.,1.),3.)*.35;',     // cool fill light
    '  lit+=col*vec3(.1,.18,.4)*clamp(dot(nw,L3)*.5+.5,0.,1.)*.25;',
    '  lit+=vec3(1.,.95,.9)*pow(max(dot(nw,hv1),0.),gloss)*spec;',
    '  lit+=vec3(.9,.95,1.)*pow(max(dot(nw,hv2),0.),gloss*.6)*spec*.5;',
    '  float fr=.03+.97*pow(1.-ndv,4.);',
    '  lit+=env(reflect(-v,nw))*fr*(isCut?.16:.40);',
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
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
  gl.useProgram(prog);
  var buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  var loc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  var U = {};
  ['uRes', 'uRot', 'uTilt', 'uCut', 'uScale'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });

  var w = 0, h = 0;
  var scheduled = 0, lastBeat = -1;
  function ramp(low, high, value) {
    var t = Math.max(0, Math.min(1, (value - low) / (high - low)));
    return t * t * (3 - 2 * t);
  }
  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 1.25) * resolution;
    w = Math.max(2, Math.round(canvas.clientWidth * dpr));
    h = Math.max(2, Math.round(canvas.clientHeight * dpr));
    canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h);
  }

  function draw(rot, cut, zoom) {
    gl.uniform2f(U.uRes, w, h);
    gl.uniform1f(U.uRot, rot);
    gl.uniform1f(U.uTilt, 0.08);
    gl.uniform1f(U.uCut, cut);
    gl.uniform1f(U.uScale, zoom || 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  var points = [
    ['Aortic arch', .46, 1.43, -.12, 'outer'],
    ['Superior vena cava', -.68, 1.21, -.10, 'outer'],
    ['Right atrium', -.63, .32, -.05, 'inner'],
    ['Tricuspid valve', -.48, .07, .13, 'inner'],
    ['Right ventricle', -.39, -.43, .20, 'inner'],
    ['Left atrium', .42, .56, -.42, 'inner'],
    ['Mitral valve', .40, .16, -.19, 'inner'],
    ['Left ventricle', .49, -.38, -.08, 'inner'],
    ['Interventricular septum', .11, -.68, .15, 'inner']
  ];
  var key = document.createElement('ol');
  key.className = 'hx-live-key';
  landmarks.appendChild(key);
  var pins = points.map(function (point, i) {
    var pin = document.createElement('span'), item = document.createElement('li');
    pin.className = 'hx-pin';
    pin.dataset.number = item.dataset.number = String(i < 2 ? i + 1 : i - 1);
    pin.textContent = item.textContent = point[0];
    pin.setAttribute('aria-hidden', 'true');
    landmarks.appendChild(pin);
    key.appendChild(item);
    return { pin: pin, item: item };
  });

  function labelView(rot, cut, zoom) {
    var cw = canvas.clientWidth, ch = canvas.clientHeight;
    var cr = Math.cos(rot), sr = Math.sin(rot), ct = Math.cos(.08), st = Math.sin(.08);
    points.forEach(function (v, i) {
      var shown = v[4] === 'outer' ? cut > 2.8 && cr > -.35 : cut < .20;
      var pin = pins[i].pin;
      pin.hidden = pins[i].item.hidden = !shown;
      if (!shown) return;
      var x = v[1] - .10, y = v[2] - .30, z = v[3];
      var tiltedZ = st * y + ct * z;
      var vx = cr * x + sr * tiltedZ, vy = ct * y - st * z;
      var depth = 6.2 - (-sr * x + cr * tiltedZ);
      var scale = 1.8 * zoom * ch / depth;
      pin.style.left = (cw / 2 + vx * scale) + 'px';
      pin.style.top = (ch / 2 - vy * scale) + 'px';
      pin.classList.toggle('pin-left', vx < 0);
    });
  }

  // Original scroll choreography: one continuous turn, slowing at the four-chamber plane.
  function pose(p) {
    var x = p - .60, ax = Math.abs(x), a = .22;
    var g = ax < a ? 9 * (.3 * ax + .7 * ax ** 3 / (3 * a * a)) : 9 * (.3 * a + .7 * a / 3 + ax - a);
    return {rot: Math.PI * 2 + Math.sign(x) * g, cut: 3 * ramp(.35, 1, g)};
  }
  var current = null, last = 0, resolution = 1, slowFrames = 0;
  function render(now) {
    scheduled = 0;
    if (gl.isContextLost()) { showStill(); return; }
    var fixed = stillView.matches;
    hero.classList.toggle('hx-static', fixed);
    section.hidden = true;
    landmarks.hidden = false;
    canvas.style.opacity = 1;
    var rect = hero.getBoundingClientRect();
    if (document.hidden || rect.bottom < 0 || rect.top > innerHeight) { last = 0; return; }
    var progress = fixed ? .60 : Math.max(0, Math.min(1, -rect.top / Math.max(1, hero.offsetHeight - innerHeight)));
    var elapsed = last ? now - last : 16;
    last = now;
    current = current === null || fixed ? progress : current + (progress - current) * (1 - Math.exp(-Math.min(70, elapsed) / 85));
    var beat = fixed || current < .16 ? 0 : current < .48 ? 1 : current < .74 ? 2 : 3;
    if (beat !== lastBeat) { showBeat(beat); lastBeat = beat; }
    var k = pose(current), ph = (now * .0011) % 1;
    var pulse = fixed ? 0 : .014 * (Math.exp(-(((ph-.08)/.05)**2)) + .6*Math.exp(-(((ph-.30)/.06)**2)));
    var rot = k.rot + (fixed ? 0 : Math.sin(now/4000)*.08*Math.min(k.cut,1));
    var zoom = (.87 + .03*k.cut/3) * (1 + pulse);
    draw(rot, k.cut, zoom);
    labelView(rot, k.cut, zoom);
    slowFrames = elapsed > 36 ? slowFrames + 1 : 0;
    if (slowFrames >= 8 && resolution > .58) { resolution *= .85; slowFrames = 0; resize(); }
    if (!fixed) schedule();
  }
  function schedule() { if (!scheduled) scheduled = requestAnimationFrame(render); }
  function reflow() {
    hero.classList.toggle('hx-static', stillView.matches);
    resize(); schedule();
  }
  window.addEventListener('resize', reflow);
  window.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('visibilitychange', schedule);
  stillView.addEventListener('change', reflow);
  if ('ResizeObserver' in window) new ResizeObserver(function () { resize(); schedule(); }).observe(canvas);
  reflow();
})();
