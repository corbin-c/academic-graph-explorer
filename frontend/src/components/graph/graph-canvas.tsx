import { useEffect, useRef, useCallback } from "react"
import * as d3 from "d3"
import type { Neighborhood, GraphEntity } from "@/lib/api"

interface GraphCanvasProps {
  neighborhood: Neighborhood | undefined
  selectedNodeId: string | null
  onSelectNode: (nodeId: string | null) => void
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
}

const TYPE_COLORS: Record<string, string> = {
  person: "var(--color-primary, #3b82f6)",
  organization: "var(--color-chart-5, #8b5cf6)",
  publication: "var(--color-chart-2, #10b981)",
}

const TYPE_RADIUS: Record<string, number> = {
  person: 8,
  organization: 9,
  publication: 6,
}

export function GraphCanvas({ neighborhood, selectedNodeId, onSelectNode }: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const onSelectNodeRef = useRef(onSelectNode)
  onSelectNodeRef.current = onSelectNode

  const selectedNodeIdRef = useRef(selectedNodeId)
  selectedNodeIdRef.current = selectedNodeId

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

    // Clear previous content
    svg.selectAll("*").remove()

    // Build D3 nodes and links
    const nodeMap = new Map<string, GraphEntity>()
    for (const n of neighborhood.nodes) {
      nodeMap.set(n.id, n)
    }

    const d3Nodes: D3Node[] = neighborhood.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      isCenter: n.id === neighborhood.center.id,
    }))

    const d3Links: D3Link[] = neighborhood.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
      }))

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
      .force("collision", d3.forceCollide(35))

    // Zoom behavior
    const g = svg.append("g")

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString())
      })

    svg.call(zoom)

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
      .attr("stroke", "var(--color-border, #d4d4d8)")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1.5)
      .selectAll<SVGLineElement, D3Link>("line")
      .data(d3Links)
      .join("line")

    // Node groups
    const nodeG = g
      .append("g")
      .selectAll<SVGGElement, D3Node>("g")
      .data(d3Nodes)
      .join("g")
      .attr("cursor", "pointer")

    // Node circles
    nodeG
      .append("circle")
      .attr("r", (d) => (d.isCenter ? 16 : TYPE_RADIUS[d.type] ?? 7))
      .attr("fill", (d) => TYPE_COLORS[d.type] ?? "var(--color-muted-foreground)")
      .attr("stroke", (d) => {
        if (d.id === selectedNodeIdRef.current) return "var(--color-chart-4, #f59e0b)"
        if (d.isCenter) return "var(--color-primary, #3b82f6)"
        return "transparent"
      })
      .attr("stroke-width", (d) => (d.isCenter || d.id === selectedNodeIdRef.current ? 3 : 0))
      .style("filter", (d) => {
        if (d.id === selectedNodeIdRef.current) return "drop-shadow(0 0 8px var(--color-chart-4, #f59e0b))"
        if (d.isCenter) return "drop-shadow(0 0 6px var(--color-primary, #3b82f6))"
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

      nodeG.attr("transform", (d) => `translate(${d.x},${d.y})`)
    })

    return () => {
      simulation.stop()
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
      circle.attr("stroke", isSelected ? "var(--color-chart-4, #f59e0b)" : d.isCenter ? "var(--color-primary, #3b82f6)" : "transparent")
      circle.attr("stroke-width", isSelected || d.isCenter ? 3 : 0)
      circle.style("filter", isSelected ? "drop-shadow(0 0 8px var(--color-chart-4, #f59e0b))" : d.isCenter ? "drop-shadow(0 0 6px var(--color-primary, #3b82f6))" : "none")
    })
  }, [selectedNodeId, neighborhood])

  // Resize observer
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const observer = new ResizeObserver(() => {
      const cleanup = renderGraph()
      return () => cleanup?.()
    })

    observer.observe(container)
    return () => observer.disconnect()
  }, [renderGraph])

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-background">
      <svg ref={svgRef} className="h-full w-full" />
    </div>
  )
}
