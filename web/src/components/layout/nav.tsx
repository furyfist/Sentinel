'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/incidents', label: 'Incidents' },
  { href: '/forensics', label: 'Forensics' },
  { href: '/quality', label: 'Quality' },
  { href: '/approvals', label: 'Approvals', badge: true },
  { href: '/risk', label: 'Risk' },
  { href: '/digest', label: 'Digest' },
  { href: '/settings', label: 'Settings' },
]

export function Nav() {
  const pathname = usePathname()
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    const fetchPending = () => {
      api.approvals.stats()
        .then(s => setPendingCount(s.pending ?? 0))
        .catch(() => {})
    }
    fetchPending()
    const interval = setInterval(fetchPending, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Image src="/logo.png" alt="Sentinel logo" width={32} height={32} className="h-8 w-8" priority />
          <div className="flex flex-col leading-none">
            <span className="font-bold text-slate-900 text-sm tracking-wide uppercase">Sentinel</span>
            <span className="text-[9px] font-medium text-indigo-500 tracking-widest uppercase">AI Observability & Response</span>
          </div>
        </div>

        <nav className="flex items-center gap-0.5">
          {links.map((link) => {
            const active = pathname === link.href || (link.href !== '/dashboard' && pathname.startsWith(link.href))
            const showBadge = link.badge && pendingCount > 0
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
                <span className="relative flex items-center gap-1.5">
                  <span
                    className={`font-medium transition-colors ${
                      active ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {link.label}
                  </span>
                  {showBadge && (
                    <span className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold bg-red-500 text-white rounded-full leading-none">
                      {pendingCount > 9 ? '9+' : pendingCount}
                    </span>
                  )}
                </span>
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
