/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './django_backend/templates/**/*.html',
    './django_backend/static/js/**/*.js',
    './home/**/*.html',
    './auth/**/*.html',
    './buyer/**/*.html',
    './seller/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        brand: {
          DEFAULT: '#16a34a',
          dark: '#15803d',
          light: '#22c55e',
          soft: '#f0fdf4',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'squircle-sm': '10px',
        'squircle-md': '14px',
        'squircle-lg': '20px',
        'squircle-xl': '28px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}
