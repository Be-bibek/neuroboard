import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Box, Environment, Plane } from '@react-three/drei';
import * as THREE from 'three';
import { useNeuroStore } from '../store/useNeuroStore';

// ── Components ─────────────────────────────────────────────────────────────

const BoardPlane = () => {
  return (
    <group>
      {/* Dark translucent glass board plane */}
      <Plane args={[300, 300]} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
        <meshPhysicalMaterial
          color="#0b0f1a"
          transparent
          opacity={0.8}
          roughness={0.2}
          metalness={0.8}
          clearcoat={1.0}
        />
      </Plane>
      {/* Cyberpunk grid overlay */}
      <Grid 
        infiniteGrid 
        fadeDistance={200} 
        sectionColor="#06b6d4" 
        cellColor="#06b6d4" 
        sectionThickness={1} 
        cellThickness={0.5} 
        position={[0, -0.49, 0]} 
      />
    </group>
  );
};

const FootprintMesh = ({ targetX, targetY }: { targetX: number, targetY: number }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Center KiCad coordinates around (0,0) by assuming an arbitrary board center if needed,
  // but for simplicity we will map directly: X = x - 150, Z = y - 100 (adjust based on board offset)
  // Let's assume the center is roughly at (150, 100).
  const offsetX = 150;
  const offsetZ = 100;

  useFrame((state, delta) => {
    if (meshRef.current) {
      // Smooth interpolation towards the target position
      const targetPos = new THREE.Vector3(targetX - offsetX, 1, targetY - offsetZ);
      meshRef.current.position.lerp(targetPos, 10 * delta);
      
      // Pulsing effect
      const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.05;
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <Box ref={meshRef} args={[4, 2, 4]} position={[targetX - offsetX, 1, targetY - offsetZ]}>
      <meshStandardMaterial 
        color="#f59e0b" 
        wireframe={true} 
        emissive="#f59e0b"
        emissiveIntensity={2}
        transparent
        opacity={0.8}
      />
    </Box>
  );
};

export const PCBViewer3D = () => {
  const boardPositions = useNeuroStore((state) => state.boardPositions);

  return (
    <div className="w-full h-full relative bg-[#050810]">
      {/* Top telemetry overlay */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <div className="text-[#06b6d4] text-xs font-mono font-bold tracking-widest uppercase flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#f59e0b] animate-pulse"></span>
          Live Holographic Sync
        </div>
        <div className="text-white/40 text-[10px] font-mono mt-1">
          {Object.keys(boardPositions).length} Telemetry Nodes Active
        </div>
      </div>

      <Canvas camera={{ position: [0, 80, 80], fov: 45 }}>
        <color attach="background" args={['#050810']} />
        
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} color="#06b6d4" />
        <pointLight position={[-10, 10, -10]} intensity={1} color="#f59e0b" />
        
        <BoardPlane />

        {/* Render Footprints */}
        {Object.entries(boardPositions).map(([ref, pos]) => (
          <FootprintMesh key={ref} targetX={pos.x} targetY={pos.y} />
        ))}

        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          enableRotate={true}
          maxPolarAngle={Math.PI / 2 - 0.05} // Don't go below ground
        />
        <Environment preset="night" />
      </Canvas>
    </div>
  );
};
