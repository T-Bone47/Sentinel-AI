/** Every color token is authored as bare OKLCH channels in index.css so that
 *  Tailwind alpha modifiers (e.g. bg-primary/12) resolve correctly. */
const token = (name) => `oklch(var(${name}) / <alpha-value>)`

export default {content: [
  './index.html',
  './src/**/*.{js,ts,jsx,tsx}'
],
  darkMode: 'selector',
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px'
      }
    },
    extend: {
      colors: {
        background: token('--background'),
        foreground: token('--foreground'),
        'surface-1': token('--surface-1'),
        'surface-2': token('--surface-2'),
        'surface-3': token('--surface-3'),
        card: token('--card'),
        'card-foreground': token('--card-foreground'),
        popover: token('--popover'),
        'popover-foreground': token('--popover-foreground'),
        primary: token('--primary'),
        'primary-hover': token('--primary-hover'),
        'primary-foreground': token('--primary-foreground'),
        'primary-soft': token('--primary-soft'),
        cyan: token('--cyan'),
        'cyan-soft': token('--cyan-soft'),
        secondary: token('--secondary'),
        'secondary-foreground': token('--secondary-foreground'),
        muted: token('--muted'),
        'muted-foreground': token('--muted-foreground'),
        accent: token('--accent'),
        'accent-foreground': token('--accent-foreground'),
        destructive: token('--destructive'),
        'destructive-foreground': token('--destructive-foreground'),
        success: token('--success'),
        warning: token('--warning'),
        info: token('--info'),
        'risk-critical': token('--risk-critical'),
        'risk-high': token('--risk-high'),
        'risk-medium': token('--risk-medium'),
        'risk-low': token('--risk-low'),
        'risk-none': token('--risk-none'),
        ai: token('--ai'),
        'ai-hover': token('--ai-hover'),
        'ai-foreground': token('--ai-foreground'),
        'ai-surface': token('--ai-surface'),
        'ai-border': token('--ai-border'),
        border: token('--border'),
        'border-strong': token('--border-strong'),
        input: token('--input'),
        ring: token('--ring'),
        'chart-1': token('--chart-1'),
        'chart-2': token('--chart-2'),
        'chart-3': token('--chart-3'),
        'chart-4': token('--chart-4'),
        'chart-5': token('--chart-5'),
        'chart-grid': token('--chart-grid'),
        sidebar: token('--sidebar'),
        'sidebar-foreground': token('--sidebar-foreground'),
        'sidebar-primary': token('--sidebar-primary'),
        'sidebar-primary-foreground': token('--sidebar-primary-foreground'),
        'sidebar-accent': token('--sidebar-accent'),
        'sidebar-accent-foreground': token('--sidebar-accent-foreground'),
        'sidebar-border': token('--sidebar-border'),
        'sidebar-ring': token('--sidebar-ring')
      },
      borderRadius: {
        sm: 'calc(var(--radius) * 0.6)',
        md: 'calc(var(--radius) * 0.8)',
        lg: 'var(--radius)',
        xl: 'calc(var(--radius) * 1.4)',
        '2xl': 'calc(var(--radius) * 1.8)',
        '3xl': 'calc(var(--radius) * 2.2)'
      },
      fontFamily: {
        heading: ['Geist', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['Geist', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'monospace']
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }]
      },
      letterSpacing: {
        label: '0.08em'
      },
      boxShadow: {
        xs: '0 1px 2px -1px hsl(var(--shadow-color) / 0.20)',
        sm: '0 1px 3px -1px hsl(var(--shadow-color) / 0.26), 0 1px 2px -2px hsl(var(--shadow-color) / 0.18)',
        md: '0 6px 16px -6px hsl(var(--shadow-color) / 0.34), 0 2px 6px -3px hsl(var(--shadow-color) / 0.22)',
        lg: '0 16px 40px -12px hsl(var(--shadow-color) / 0.44), 0 4px 12px -6px hsl(var(--shadow-color) / 0.26)',
        xl: '0 32px 72px -24px hsl(var(--shadow-color) / 0.60)'
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' }
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 var(--ai-glow)' },
          '70%': { boxShadow: '0 0 0 10px transparent' },
          '100%': { boxShadow: '0 0 0 0 transparent' }
        },
        /* Live monitoring dot */
        'signal-pulse': {
          '0%,100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.35', transform: 'scale(0.82)' }
        },
        'signal-ping': {
          '0%': { opacity: '0.6', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(2.6)' }
        },
        /* Trust score scanning ring */
        'scan-rotate': {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' }
        },
        /* Telemetry sweep across a panel */
        sweep: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(300%)' }
        },
        /* Data-flow dash along a path */
        'dash-flow': {
          to: { strokeDashoffset: '-24' }
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        }
      },
      animation: {
        shimmer: 'shimmer 1.8s infinite',
        'pulse-ring': 'pulse-ring 2.4s ease-out infinite',
        'signal-pulse': 'signal-pulse 2s ease-in-out infinite',
        'signal-ping': 'signal-ping 2.4s ease-out infinite',
        'scan-rotate': 'scan-rotate 8s linear infinite',
        'scan-slow': 'scan-rotate 22s linear infinite',
        sweep: 'sweep 2.6s ease-in-out infinite',
        'dash-flow': 'dash-flow 1s linear infinite',
        'fade-up': 'fade-up 0.24s ease-out both'
      },
      transitionDuration: {
        180: '180ms',
        220: '220ms'
      }
    }
  }
}
