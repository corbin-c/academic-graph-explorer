import { BrowserRouter, Routes, Route } from "react-router-dom"
import { HomePage } from "@/pages/home"
import { GraphPage } from "@/pages/graph"

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/graph/:entityId" element={<GraphPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
