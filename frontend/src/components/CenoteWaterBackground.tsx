import { useEffect, useRef } from "react";

// Shader portado de un proyecto de Claude Design ("Cenote Water Background").
// Simula la superficie de un cenote: campo de olas sumado a partir de 5
// direcciones/frecuencias, iluminación especular (glint dorado + reflejo
// turquesa) y motas de partícula que derivan lentamente. Todo el color sale
// del propio GLSL -- no hay imagen ni video de por medio.
const VERT = `
attribute vec2 aPos;
void main(){ gl_Position = vec4(aPos,0.0,1.0); }
`;

const FRAG = `
precision highp float;
uniform vec2 uRes;
uniform float uPhase;
uniform vec3 uTurquoise;
uniform vec3 uAmber;
uniform vec3 uDeep;
uniform float uParticles;
#define PI 6.28318530718

float hash(vec2 p){
  return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453123);
}

void waveField(vec2 uv, float t, out float height, out vec2 grad){
  vec2 dirs[5];
  dirs[0]=normalize(vec2(1.0,0.35));
  dirs[1]=normalize(vec2(-0.6,0.8));
  dirs[2]=normalize(vec2(0.3,-0.95));
  dirs[3]=normalize(vec2(0.9,-0.2));
  dirs[4]=normalize(vec2(-0.8,-0.5));
  float freqs[5]; freqs[0]=3.0; freqs[1]=4.5; freqs[2]=6.2; freqs[3]=8.7; freqs[4]=11.5;
  float amps[5]; amps[0]=0.5; amps[1]=0.35; amps[2]=0.22; amps[3]=0.14; amps[4]=0.09;

  height = 0.0;
  grad = vec2(0.0);
  for (int i = 0; i < 5; i++){
    float k = float(i+1);
    float ph = dot(uv, dirs[i]) * freqs[i] + t * k;
    height += amps[i] * sin(ph);
    grad += amps[i] * freqs[i] * dirs[i] * cos(ph);
  }
}

void main(){
  vec2 uv0 = (gl_FragCoord.xy - 0.5*uRes) / min(uRes.x, uRes.y);
  vec2 uv = uv0 * 2.4;
  float t = uPhase;

  float height; vec2 grad;
  waveField(uv, t, height, grad);

  vec3 normal = normalize(vec3(-grad.x, -grad.y, 1.7));
  vec3 lightDir = normalize(vec3(0.35, 0.55, 0.75));
  float ndotl = max(dot(normal, lightDir), 0.0);
  float softSpec = pow(ndotl, 6.0);
  float tightSpec = pow(ndotl, 55.0);

  vec3 col = uDeep * mix(0.8, 1.08, height*0.5+0.5);
  col = mix(col, uTurquoise, clamp(softSpec * 1.9, 0.0, 1.0));
  col += uAmber * tightSpec * 1.5;
  col += uTurquoise * tightSpec * 0.5;

  vec2 puv = uv0 * 10.0;
  vec2 pcell = floor(puv);
  vec2 pf = fract(puv);
  float pval = 0.0;
  for (int dx=-1; dx<=1; dx++){
    for (int dy=-1; dy<=1; dy++){
      vec2 cell = pcell + vec2(float(dx), float(dy));
      float h = hash(cell);
      vec2 driftDir = vec2(sin(h*PI), cos(h*PI));
      vec2 pos = vec2(float(dx), float(dy)) + driftDir * (0.4 + 0.3*sin(uPhase + h*PI)) - pf;
      float d = length(pos);
      float speck = smoothstep(0.035, 0.0, d) * h;
      pval += speck;
    }
  }
  col += uTurquoise * pval * 0.18 * uParticles;

  float vign = 1.0 - smoothstep(0.3, 1.0, length(uv0));
  col *= mix(0.12, 1.0, vign);

  gl_FragColor = vec4(col, 1.0);
}
`;

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const full = clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean;
  const n = parseInt(full, 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

interface CenoteWaterBackgroundProps {
  className?: string;
  turquoiseColor?: string;
  amberColor?: string;
  deepColor?: string;
  speed?: number;
  particleDensity?: number;
}

const PERIOD = 26;

export function CenoteWaterBackground({
  className,
  turquoiseColor = "#2fe0c8",
  amberColor = "#e8b062",
  deepColor = "#02201c",
  speed = 1.4,
  particleDensity = 0.8,
}: CenoteWaterBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", { antialias: true, alpha: false });
    if (!gl) return;

    const compile = (type: number, src: string) => {
      const shader = gl.createShader(type)!;
      gl.shaderSource(shader, src);
      gl.compileShader(shader);
      return shader;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(prog, "aPos");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(prog, "uRes");
    const uPhase = gl.getUniformLocation(prog, "uPhase");
    const uTurquoise = gl.getUniformLocation(prog, "uTurquoise");
    const uAmber = gl.getUniformLocation(prog, "uAmber");
    const uDeep = gl.getUniformLocation(prog, "uDeep");
    const uParticles = gl.getUniformLocation(prog, "uParticles");

    // El canvas sigue el tamaño real de la card (no el viewport completo:
    // el diseño original era un fondo de página entera).
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
      const height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    const turquoiseRgb = hexToRgb(turquoiseColor);
    const amberRgb = hexToRgb(amberColor);
    const deepRgb = hexToRgb(deepColor);

    const drawFrame = (phase: number) => {
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uPhase, phase);
      gl.uniform3fv(uTurquoise, turquoiseRgb);
      gl.uniform3fv(uAmber, amberRgb);
      gl.uniform3fv(uDeep, deepRgb);
      gl.uniform1f(uParticles, particleDensity);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    drawFrame(0);

    let raf = 0;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const start = performance.now();
      const loop = () => {
        const t = (((performance.now() - start) / 1000) * speed) % PERIOD;
        drawFrame((t / PERIOD) * Math.PI * 2);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      if (raf) cancelAnimationFrame(raf);
      resizeObserver.disconnect();
    };
  }, [turquoiseColor, amberColor, deepColor, speed, particleDensity]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
