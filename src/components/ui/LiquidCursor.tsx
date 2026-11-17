import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring, useVelocity, useTransform, useAnimationFrame } from 'framer-motion';
import { cn } from '../../utils/cn';

export function LiquidCursor() {
  const [isTouch, setIsTouch] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [hoverLabel, setHoverLabel] = useState<string | null>(null);
  const [isClicking, setIsClicking] = useState(false);

  // Mouse coordinates
  const mouseX = useMotionValue(typeof window !== 'undefined' ? window.innerWidth / 2 : 0);
  const mouseY = useMotionValue(typeof window !== 'undefined' ? window.innerHeight / 2 : 0);

  // Smooth springs for position
  const springConfig = { damping: 25, stiffness: 300, mass: 0.5 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);

  // Velocity tracking
  const velocityX = useVelocity(smoothX);
  const velocityY = useVelocity(smoothY);

  // Derive stretch and rotation from velocity
  const rotation = useMotionValue(0);
  const scaleX = useMotionValue(1);
  const scaleY = useMotionValue(1);

  useAnimationFrame(() => {
    const vx = velocityX.get();
    const vy = velocityY.get();
    const speed = Math.sqrt(vx * vx + vy * vy);
    
    // Stretch logic: more speed = more stretch horizontally, squish vertically
    const maxStretch = 1.6;
    const stretch = 1 + Math.min(speed / 3000, maxStretch - 1);
    
    // Smooth out scaling if hovering or clicking to maintain shape better
    if (isHovering || isClicking) {
      scaleX.set(1);
      scaleY.set(1);
    } else {
      scaleX.set(stretch);
      scaleY.set(1 / stretch);
    }

    // Angle calculation
    if (speed > 50 && !isHovering && !isClicking) {
      const angle = Math.atan2(vy, vx);
      rotation.set(angle);
    }
  });

  // Global listeners
  useEffect(() => {
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    setIsTouch(isTouchDevice);

    if (isTouchDevice) return;

    const handleMouseMove = (e: MouseEvent) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };

    const handleMouseDown = () => setIsClicking(true);
    const handleMouseUp = () => setIsClicking(false);

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Look for clickable elements or explicit data-cursor targets
      const clickable = target.closest('a, button, input, [data-cursor-hover], [role="button"], [role="tab"], [role="switch"]');
      
      if (clickable) {
        setIsHovering(true);
        const label = clickable.getAttribute('data-cursor-label');
        if (label) {
          setHoverLabel(label);
        } else if (clickable.tagName === 'BUTTON' || clickable.tagName === 'A' || clickable.getAttribute('role') === 'button') {
          // You can set a default label here, but minimal is usually better unless explicitly labeled.
          setHoverLabel(null);
        } else {
          setHoverLabel(null);
        }
      } else {
        setIsHovering(false);
        setHoverLabel(null);
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mousedown', handleMouseDown, { passive: true });
    window.addEventListener('mouseup', handleMouseUp, { passive: true });
    window.addEventListener('mouseover', handleMouseOver, { passive: true });

    // Inject global style to hide native cursor everywhere, including on pointers
    const style = document.createElement('style');
    style.id = 'liquid-cursor-style';
    style.innerHTML = `
      * {
        cursor: none !important;
      }
    `;
    document.head.appendChild(style);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseover', handleMouseOver);
      const injectedStyle = document.getElementById('liquid-cursor-style');
      if (injectedStyle) {
        injectedStyle.remove();
      }
    };
  }, [mouseX, mouseY]);

  if (isTouch) return null;

  // Sizes
  const defaultSize = 20;
  const hoverSize = 64;
  const clickSize = 16;
  const currentSize = isClicking ? clickSize : isHovering ? hoverSize : defaultSize;

  // We offset the rendering by half size to center it on the mouse pointer
  const offset = currentSize / 2;
  const renderX = useTransform(smoothX, (v) => v - offset);
  const renderY = useTransform(smoothY, (v) => v - offset);

  // Droplets configuration for click splash
  const droplets = [
    { id: 1, angle: 0, dist: 30 },
    { id: 2, angle: Math.PI / 2, dist: 35 },
    { id: 3, angle: Math.PI, dist: 30 },
    { id: 4, angle: (3 * Math.PI) / 2, dist: 35 },
    { id: 5, angle: Math.PI / 4, dist: 40 },
    { id: 6, angle: (5 * Math.PI) / 4, dist: 40 },
  ];

  return (
    <>
      <svg className="hidden">
        <defs>
          <filter id="liquid-goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feColorMatrix
              in="blur"
              mode="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 25 -9"
              result="liquid-goo"
            />
            <feBlend in="SourceGraphic" in2="liquid-goo" />
          </filter>
        </defs>
      </svg>

      <div
        className="pointer-events-none fixed inset-0 z-[9999]"
        style={{ filter: 'url(#liquid-goo)' }}
      >
        <motion.div
          className="absolute left-0 top-0 rounded-full mix-blend-difference"
          style={{
            x: renderX,
            y: renderY,
            width: currentSize,
            height: currentSize,
            rotate: rotation,
            scaleX,
            scaleY,
            backgroundColor: 'white', // White with mix-blend-difference is great, but we can also use primary color if preferred.
            transformOrigin: 'center center',
          }}
          animate={{
            width: currentSize,
            height: currentSize,
            opacity: isHovering ? 0.3 : 1,
          }}
          transition={{
            width: { type: 'spring', stiffness: 400, damping: 25 },
            height: { type: 'spring', stiffness: 400, damping: 25 },
            opacity: { duration: 0.2 },
          }}
        />

        {/* Droplets for click splash */}
        {droplets.map((drop) => {
          const dx = Math.cos(drop.angle) * drop.dist;
          const dy = Math.sin(drop.angle) * drop.dist;
          return (
            <motion.div
              key={drop.id}
              className="absolute left-0 top-0 rounded-full bg-white mix-blend-difference"
              style={{
                x: useTransform(smoothX, (v) => v - 4),
                y: useTransform(smoothY, (v) => v - 4),
                width: 8,
                height: 8,
              }}
              animate={
                isClicking
                  ? { x: smoothX.get() - 4 + dx, y: smoothY.get() - 4 + dy, scale: 1 }
                  : { scale: 0 }
              }
              transition={{
                type: 'spring',
                stiffness: 300,
                damping: 20,
              }}
            />
          );
        })}
      </div>

      {/* Label container (kept outside the goo filter so text remains crisp) */}
      <motion.div
        className="pointer-events-none fixed z-[10000] flex items-center justify-center font-mono text-[10px] font-bold tracking-widest text-primary mix-blend-difference"
        style={{
          x: useTransform(smoothX, (v) => v - hoverSize / 2),
          y: useTransform(smoothY, (v) => v - hoverSize / 2),
          width: hoverSize,
          height: hoverSize,
        }}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{
          opacity: isHovering && hoverLabel ? 1 : 0,
          scale: isHovering && hoverLabel ? 1 : 0.8,
        }}
        transition={{ duration: 0.2 }}
      >
        {hoverLabel}
      </motion.div>
    </>
  );
}
