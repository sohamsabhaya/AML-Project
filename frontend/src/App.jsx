import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layout/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import NewAnalysis from './pages/NewAnalysis.jsx'
import Results from './pages/Results.jsx'
import History from './pages/History.jsx'
import Report from './pages/Report.jsx'
import Settings from './pages/Settings.jsx'
import Insights from './pages/Insights.jsx'
import Compare from './pages/Compare.jsx'

// Routes are fixed by the lead. Each page is owned by one agent (see docs/API_CONTRACT.md).
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/analyze" element={<NewAnalysis />} />
        <Route path="/results/:id" element={<Results />} />
        <Route path="/history" element={<History />} />
        <Route path="/report/:id" element={<Report />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

