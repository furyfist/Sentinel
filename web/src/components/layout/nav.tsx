'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'

const links = [
  { href: '/', label: 'Dashboard' },
  { href: '/incidents', label: 'Incidents' },
  { href: '/forensics', label: 'Forensics' },
  { href: '/risk', label: 'Risk' },
  { href: '/digest', label: 'Digest' },
  { href: '/settings', label: 'Settings' },
]

export function Nav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
            <span className="text-white text-xs font-bold tracking-tight">S</span>
          </div>
          <span className="font-semibold text-slate-900 text-sm">Sentinel</span>
        </div>

        <nav className="flex items-center gap-0.5">
          {links.map((link) => {
            const active =
              link.href === '/'
                ? pathname === '/'
                : pathname.startsWith(link.href)
            return (
              <Link
                key={link.href}
                href={link.href}
                className="relative px-3 py-1.5 text-sm rounded-md transition-colors"
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 bg-indigo-50 rounded-md"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span
                  className={`relative font-medium transition-colors ${
                    active ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {link.label}
                </span>
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
