const { heroui } = require("@heroui/react")

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
      "./index.html",
      "./src/**/*.{ts,tsx,js,jsx}",
      "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
    ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		boxShadow: {
  			soft: '0 2px 10px -2px rgba(20, 90, 105, 0.12), 0 1px 3px -1px rgba(20, 90, 105, 0.08)',
  			'soft-lg': '0 10px 26px -14px rgba(20, 90, 105, 0.14)',
  			aero: '0 10px 26px -18px rgba(16, 92, 110, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.5)',
  			glow: '0 0 0 1px rgba(255,255,255,0.25), 0 6px 18px -12px rgba(20, 160, 160, 0.20)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			surface: 'hsl(var(--surface))',
  			elevated: 'hsl(var(--elevated))',
  			'text-secondary': 'hsl(var(--text-secondary))',
  			'text-muted': 'hsl(var(--text-muted))',
  			positive: 'hsl(var(--positive))',
  			warning: 'hsl(var(--warning))',
  			negative: 'hsl(var(--negative))',
  			aqua: 'hsl(var(--aqua))',
  			lagoon: 'hsl(var(--lagoon))',
  			brand: {
  				DEFAULT: 'hsl(var(--brand))',
  				foreground: 'hsl(var(--brand-foreground))'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			sidebar: {
  				DEFAULT: 'hsl(var(--sidebar-background))',
  				foreground: 'hsl(var(--sidebar-foreground))',
  				primary: 'hsl(var(--sidebar-primary))',
  				'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
  				accent: 'hsl(var(--sidebar-accent))',
  				'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
  				border: 'hsl(var(--sidebar-border))',
  				ring: 'hsl(var(--sidebar-ring))'
  			}
  		},
  		fontFamily: {
  			heading: ['var(--font-heading)'],
  			body: ['var(--font-body)'],
  			display: ['var(--font-display)'],
  			mono: ['var(--font-mono)']
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			ripple: {
  				'0%, 100%': { transform: 'translate(-50%, -50%) scale(1)' },
  				'50%': { transform: 'translate(-50%, -50%) scale(0.92)' }
  			}
  			},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			ripple: 'ripple 3.4s ease-in-out infinite'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate"), heroui({ addCommonColors: false })],
}
