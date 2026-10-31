// Hook: returns true when the app is running on demo data (backend unreachable or VITE_USE_MOCK=true).
import { useEffect, useState } from 'react'
import { detectDemoMode, isDemoMode } from './api.js'

export function useDemoMode() {
  const [demo, setDemo] = useState(isDemoMode())
  useEffect(() => {
    let active = true
    detectDemoMode().then((value) => active && setDemo(value))
    return () => {
      active = false
    }
  }, [])
  return demo
}
