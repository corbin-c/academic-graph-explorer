import { useEffect, useRef, useCallback } from "react"
import * as d3 from "d3"
import type { Neighborhood, GraphEntity } from "@/lib/api"

interface GraphCanvasProps {
  neighborhood: Neighborhood | undefined
  selectedNodeId: string | null
  onSelectNode: (nodeId: string | null) => void
  searchQuery: string
}

interface D3Node extends d3.SimulationNodeDatum {
  id: string
  label: string
  type: string
  isCenter: boolean
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  source: string | D3Node
  target: string | D3Node
  type: string
  targetLabel: string
}

const TYPE_COLORS: Record<string, string> = {
  person: "var(--red)",
  organization: "var(--blue)",
  publication: "var(--purple)",
}

const TYPE_RADIUS: Record<string, number> = {
  person: 8,
  organization: 9,
  publication: 6,
}

function degreeScale(deg: number): number {
  return deg <= 1 ? 1 : 1 + Math.log2(deg) * 0.5
}

export function GraphCanvas({
  neighborhood,
  selectedNodeId,
  onSelectNode,
  searchQuery,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const onSelectNodeRef = useRef(onSelectNode)
  onSelectNodeRef.current = onSelectNode

  const selectedNodeIdRef = useRef(selectedNodeId)
  selectedNodeIdRef.current = selectedNodeId

  const simulationRef = useRef<d3.Simulation<D3Node, D3Link> | null>(null)
  const positionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())

  const renderGraph = useCallback(() => {
    const svg = d3.select(svgRef.current!)
    const container = containerRef.current!
    const width = container.clientWidth
    const height = container.clientHeight

    if (!neighborhood || !neighborhood.nodes.length) {
      svg.selectAll("*").remove()
      svg
        .append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("class", "fill-muted-foreground text-sm")
        .text("No graph data available.")
      return
    }

    // Preserve current zoom/pan across re-renders
    const savedTransform = d3.zoomTransform(svgRef.current!)

    // Clear previous content
    svg.selectAll("*").remove()

    // Build D3 nodes and links
    const nodeMap = new Map<string, GraphEntity>()
    for (const n of neighborhood.nodes) {
      nodeMap.set(n.id, n)
    }

    const d3Nodes: D3Node[] = neighborhood.nodes.map((n) => {
      const prev = positionsRef.current.get(n.id)
      return {
        id: n.id,
        label: n.label,
        type: n.type,
        isCenter: n.id === neighborhood.center.id,
        x: prev?.x,
        y: prev?.y,
      }
    })

    const d3Links: D3Link[] = neighborhood.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type,
        targetLabel: nodeMap.get(e.target)?.label ?? e.target,
      }))

    // Compute degree (edge count) per node for sizing
    const degreeMap = new Map<string, number>()
    for (const e of d3Links) {
      const sId = typeof e.source === "string" ? e.source : (e.source as D3Node).id
      const tId = typeof e.target === "string" ? e.target : (e.target as D3Node).id
      degreeMap.set(sId, (degreeMap.get(sId) ?? 0) + 1)
      degreeMap.set(tId, (degreeMap.get(tId) ?? 0) + 1)
    }

    // Simulation
    const simulation = d3
      .forceSimulation<D3Node>(d3Nodes)
      .force(
        "link",
        d3
          .forceLink<D3Node, D3Link>(d3Links)
          .id((d) => d.id)
          .distance(80)
      )
      .force("charge", d3.forceManyBody().strength(-350))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide<D3Node>().radius((d) => {
        const base = d.isCenter ? 16 : (TYPE_RADIUS[d.type] ?? 7)
        const deg = degreeMap.get(d.id) ?? 0
        const scale = degreeScale(deg)
        return base * scale + 20
      }))

    simulationRef.current = simulation

    // Zoom behavior
    const g = svg.append("g")
    gRef.current = g

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString())
      })

    svg.call(zoom)
    zoomRef.current = zoom
    svg.call(zoom.transform, savedTransform)

    // Click on empty space to deselect
    svg.on("click", (event) => {
      // Only if clicking on the SVG background, not on a node
      if (event.target === svgRef.current) {
        onSelectNodeRef.current(null)
      }
    })

    // Links
    const link = g
      .append("g")
      .attr("stroke", "var(--color-border)")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1.5)
      .selectAll<SVGLineElement, D3Link>("line")
      .data(d3Links)
      .join("line")

    // Edge tooltips
    link.append("title").text((d) => `${d.type} → ${d.targetLabel}`)

    // Wider invisible hover target for easier interaction
    const linkHitArea = g
      .append("g")
      .selectAll<SVGLineElement, D3Link>("line")
      .data(d3Links)
      .join("line")
      .attr("stroke", "transparent")
      .attr("stroke-width", 12)
      .attr("cursor", "default")

    linkHitArea.append("title").text((d) => `${d.type} → ${d.targetLabel}`)

    // Node groups
    const nodeG = g
      .append("g")
      .selectAll<SVGGElement, D3Node>("g")
      .data(d3Nodes)
      .join("g")
      .attr("cursor", "pointer")
      .attr("class", "graph-node")

    // Node circles
    nodeG
      .append("circle")
      .attr("r", (d) => {
        const base = d.isCenter ? 16 : (TYPE_RADIUS[d.type] ?? 7)
        const deg = degreeMap.get(d.id) ?? 0
        const scale = degreeScale(deg)
        return base * scale
      })
      .attr(
        "fill",
        (d) => TYPE_COLORS[d.type] ?? "var(--color-muted-foreground)"
      )
      .attr("stroke", (d) => {
        if (d.id === selectedNodeIdRef.current) return "var(--amber)"
        return "transparent"
      })
      .attr("stroke-width", (d) =>
        d.isCenter || d.id === selectedNodeIdRef.current ? 3 : 0
      )
      .style("filter", (d) => {
        if (d.id === selectedNodeIdRef.current)
          return "drop-shadow(0 0 8px var(--amber))"
        return "none"
      })

    // Hover titles
    nodeG.append("title").text((d) => d.label)

    // Click handler
    nodeG.on("click", (event, d) => {
      event.stopPropagation()
      onSelectNodeRef.current(d.id)
    })

    // Drag behavior
    const drag = d3
      .drag<SVGGElement, D3Node>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on("drag", (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      })

    nodeG.call(drag)

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as D3Node).x!)
        .attr("y1", (d) => (d.source as D3Node).y!)
        .attr("x2", (d) => (d.target as D3Node).x!)
        .attr("y2", (d) => (d.target as D3Node).y!)

      linkHitArea
        .attr("x1", (d) => (d.source as D3Node).x!)
        .attr("y1", (d) => (d.source as D3Node).y!)
        .attr("x2", (d) => (d.target as D3Node).x!)
        .attr("y2", (d) => (d.target as D3Node).y!)

      nodeG.attr("transform", (d) => `translate(${d.x},${d.y})`)
    })

    return () => {
      for (const node of d3Nodes) {
        if (node.x != null && node.y != null) {
          positionsRef.current.set(node.id, { x: node.x, y: node.y })
        }
      }
      simulation.stop()
      simulationRef.current = null
      svg.on(".zoom", null)
      svg.on("click", null)
    }
  }, [neighborhood])

  // Re-render when data changes
  useEffect(() => {
    const cleanup = renderGraph()
    return () => {
      cleanup?.()
    }
  }, [renderGraph])

  // Update selection highlight without full re-render
  useEffect(() => {
    if (!svgRef.current || !neighborhood) return
    const svg = d3.select(svgRef.current)
    svg.selectAll<SVGCircleElement, D3Node>("g circle").each(function (d) {
      const circle = d3.select(this)
      const isSelected = d.id === selectedNodeId
      circle.attr("stroke", isSelected ? "var(--amber)" : "transparent")
      circle.attr("stroke-width", isSelected || d.isCenter ? 3 : 0)
      circle.style(
        "filter",
        isSelected ? "drop-shadow(0 0 8px var(--amber))" : "none"
      )
    })
  }, [selectedNodeId, neighborhood])

  // Search highlighting
  useEffect(() => {
    if (!svgRef.current || !neighborhood) return
    const svg = d3.select(svgRef.current)
    const q = searchQuery.trim().toLowerCase()

    if (!q) {
      // Reset glow for non-selected nodes
      svg.selectAll<SVGCircleElement, D3Node>(".graph-node circle").each(function (d) {
        if (d.id === selectedNodeId) return
        const circle = d3.select(this)
        circle.attr("stroke", "transparent")
        circle.attr("stroke-width", 0)
        circle.style("filter", "none")
      })
      return
    }

    const matchedPositions: Array<{ x: number; y: number }> = []

    svg.selectAll<SVGCircleElement, D3Node>(".graph-node circle").each(function (d) {
      if (d.id === selectedNodeId) return // don't override selection glow
      const circle = d3.select(this)
      if (d.label.toLowerCase().includes(q)) {
        matchedPositions.push({ x: d.x ?? 0, y: d.y ?? 0 })
        circle.attr("stroke", "var(--emerald)")
        circle.attr("stroke-width", 3)
        circle.style("filter", "drop-shadow(0 0 8px var(--emerald))")
      } else {
        circle.attr("stroke", "transparent")
        circle.attr("stroke-width", 0)
        circle.style("filter", "none")
      }
    })

    if (matchedPositions.length > 0 && zoomRef.current) {
      const w = containerRef.current!.clientWidth
      const h = containerRef.current!.clientHeight

      const xs = matchedPositions.map((m) => m.x)
      const ys = matchedPositions.map((m) => m.y)
      const minX = Math.min(...xs)
      const minY = Math.min(...ys)
      const maxX = Math.max(...xs)
      const maxY = Math.max(...ys)

      const centerX = (maxX + minX) / 2
      const centerY = (maxY + minY) / 2
      const scale =
        0.9 /
        Math.max((maxX - minX + 80) / w, (maxY - minY + 80) / h, 0.15)

      svg
        .transition()
        .duration(500)
        .call(
          zoomRef.current.transform,
          d3.zoomIdentity
            .translate(w / 2, h / 2)
            .scale(scale)
            .translate(-centerX, -centerY),
        )
    }
  }, [searchQuery, neighborhood, selectedNodeId])

  // Resize observer — recenter the existing simulation without rebuilding
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const observer = new ResizeObserver(() => {
      const sim = simulationRef.current
      if (!sim) return
      const width = container.clientWidth
      const height = container.clientHeight
      sim.force("center", d3.forceCenter(width / 2, height / 2))
      sim.alpha(0.3).restart()
    })

    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-background"
    >
      <svg ref={svgRef} className="h-full w-full" />
    </div>
  )
}
