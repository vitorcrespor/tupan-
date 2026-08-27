import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * Ceres voice orb — a round mesh sphere displaced by animated 3D simplex noise.
 * Pure three.js, self-contained, cleans up on unmount.
 */

// Ashima 3D simplex noise (MIT) — compact, GPU-side.
const SNOISE = `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0);
  const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy));
  vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);
  vec3 l=1.0-g;
  vec3 i1=min(g.xyz,l.zxy);
  vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;
  vec3 x2=x0-i2+C.yyy;
  vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(
    i.z+vec4(0.0,i1.z,i2.z,1.0))
    +i.y+vec4(0.0,i1.y,i2.y,1.0))
    +i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857;
  vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);
  vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy;
  vec4 y=y_*ns.x+ns.yyyy;
  vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);
  vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0;
  vec4 s1=floor(b1)*2.0+1.0;
  vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;
  vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);
  vec3 p1=vec3(a0.zw,h.y);
  vec3 p2=vec3(a1.xy,h.z);
  vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
  m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}
`;

const VERT = `
uniform float uTime;
uniform float uAmp;
uniform float uFreq;
varying vec3 vNormal;
varying float vDisp;
varying vec3 vView;
${SNOISE}
void main(){
  vec3 p = normalize(position);
  float n1 = snoise(p * uFreq + vec3(0.0, 0.0, uTime * 0.25));
  float n2 = snoise(p * uFreq * 2.0 + vec3(uTime * 0.18, 0.0, 0.0));
  float disp = n1 * 0.7 + n2 * 0.3;
  vDisp = disp;
  vec3 displaced = position * (1.0 + disp * uAmp);
  // recompute a smooth-ish normal from the displaced field
  vec3 tangent = normalize(cross(normal, vec3(0.0,1.0,0.0) + step(abs(normal.y),0.99)*vec3(1.0,0.0,0.0)));
  vec3 bitang = normalize(cross(normal, tangent));
  float eps = 0.08;
  vec3 nb = normalize(position + tangent*eps);
  vec3 nc = normalize(position + bitang*eps);
  float db = (snoise(nb*uFreq+vec3(0.0,0.0,uTime*0.25))*0.7 + snoise(nb*uFreq*2.0+vec3(uTime*0.18,0.0,0.0))*0.3);
  float dc = (snoise(nc*uFreq+vec3(0.0,0.0,uTime*0.25))*0.7 + snoise(nc*uFreq*2.0+vec3(uTime*0.18,0.0,0.0))*0.3);
  vec3 dbp = nb*(1.0+db*uAmp) - displaced;
  vec3 dcp = nc*(1.0+dc*uAmp) - displaced;
  vNormal = normalize(normalMatrix * normalize(cross(dbp, dcp)));
  vec4 mv = modelViewMatrix * vec4(displaced, 1.0);
  vView = -mv.xyz;
  gl_Position = projectionMatrix * mv;
}
`;

const FRAG = `
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uRim;
varying vec3 vNormal;
varying float vDisp;
varying vec3 vView;
void main(){
  vec3 N = normalize(vNormal);
  vec3 L = normalize(vec3(0.5, 0.7, 0.9));
  float diff = max(dot(N, L), 0.0);
  float fres = pow(1.0 - max(dot(N, normalize(vView)), 0.0), 2.2);
  vec3 base = mix(uColorA, uColorB, clamp(vDisp * 0.5 + 0.5, 0.0, 1.0));
  vec3 col = base * (0.45 + diff * 0.55) + uRim * fres * 0.65;
  gl_FragColor = vec4(col, 1.0);
}
`;

export default function OrbModel({ size = 34, className = '' }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(size, size, false);
    renderer.domElement.style.width = `${size}px`;
    renderer.domElement.style.height = `${size}px`;
    renderer.domElement.style.borderRadius = '50%';
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.z = 3.0;

    const root = new THREE.Group();
    scene.add(root);

    const geo = new THREE.IcosahedronGeometry(1, 32);
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uAmp: { value: 0.16 },
        uFreq: { value: 2.2 },
        uColorA: { value: new THREE.Color('#3fd6c8') },
        uColorB: { value: new THREE.Color('#2fb6e6') },
        uRim: { value: new THREE.Color('#bdf4ff') },
      },
      vertexShader: VERT,
      fragmentShader: FRAG,
    });
    const mesh = new THREE.Mesh(geo, mat);
    root.add(mesh);

    // soft outer halo ring
    const haloGeo = new THREE.SphereGeometry(1.18, 48, 48);
    const haloMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#7fe9ef'),
      transparent: true,
      opacity: 0.08,
      side: THREE.BackSide,
    });
    const halo = new THREE.Mesh(haloGeo, haloMat);
    root.add(halo);

    let raf;
    const animate = () => {
      const t = performance.now() / 1000;
      mat.uniforms.uTime.value = t;
      root.rotation.y += 0.0035;
      root.rotation.x = Math.sin(t * 0.4) * 0.14;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      renderer.dispose();
      geo.dispose();
      mat.dispose();
      haloGeo.dispose();
      haloMat.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [size]);

  return (
    <div
      ref={mountRef}
      className={`shrink-0 ${className}`}
      style={{ width: size, height: size }}
    />
  );
}