import { Nav } from '@/components/layout/nav'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Nav />
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </>
  )
}
