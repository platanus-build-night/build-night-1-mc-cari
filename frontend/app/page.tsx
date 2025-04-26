"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Bot, Code } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const MODEL_OPTIONS = [
  { value: "o3-mini", label: "O3 Mini" },
  { value: "claude-3-7-sonnet-20250219", label: "Claude 3 Sonnet"},
  { value: "o1", label: "O1" },
]

export default function LandingPage() {
  const [participants, setParticipants] = useState<number>(2)
  const [numProblems, setNumProblems] = useState<number>(4)
  const [selectedModels, setSelectedModels] = useState<string[]>(Array(4).fill("o3-mini"))
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const router = useRouter()

  const handleModelChange = (index: number, value: string) => {
    const newModels = [...selectedModels]
    newModels[index] = value
    setSelectedModels(newModels)
  }

  const handleStartCompetition = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/problems?num_problems=${numProblems}`, {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error("Error al obtener los problemas")
      }

      const problems = await response.json()
      const activeModels = selectedModels.slice(0, participants)
      
      const participantsData = activeModels.map((model, index) => ({
        id: `participant-${index + 1}`,
        model: model
      }))
      
      router.push(`/competition?participants=${participants}&problems=${encodeURIComponent(JSON.stringify(problems))}&models=${encodeURIComponent(JSON.stringify(participantsData))}`)
    } catch (error) {
      console.error("Error al obtener los problemas:", error)
      alert("Error al obtener los problemas. Por favor, asegúrese de que el servidor API esté ejecutándose en localhost:8000.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-b from-background to-muted">
      <div className="max-w-3xl w-full space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Competencia de Programación con LLM 🎈</h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Organiza competencias de programación donde los modelos de lenguaje compiten para resolver desafíos de código.
          </p>
        </div>

        <Card className="w-full">
          <CardHeader>
            <CardTitle>Configuración de la Competencia</CardTitle>
            <CardDescription>Configura los ajustes de tu competencia</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label htmlFor="participants" className="text-sm font-medium">
                  Número de Participantes
                </label>
                <span className="text-2xl font-bold">{participants}</span>
              </div>
              <Slider
                id="participants"
                min={1}
                max={3}
                step={1}
                value={[participants]}
                onValueChange={(value: number[]) => setParticipants(value[0])}
                className="py-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1</span>
                <span>2</span>
                <span>3</span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label htmlFor="problems" className="text-sm font-medium">
                  Número de Problemas
                </label>
                <span className="text-2xl font-bold">{numProblems}</span>
              </div>
              <Slider
                id="problems"
                min={1}
                max={6}
                step={1}
                value={[numProblems]}
                onValueChange={(value: number[]) => setNumProblems(value[0])}
                className="py-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1</span>
                <span>2</span>
                <span>3</span>
                <span>4</span>
                <span>5</span>
                <span>6</span>
              </div>
            </div>

            <div className="space-y-4">
              {Array.from({ length: participants }).map((_, index) => (
                <div key={index} className="flex items-center gap-4">
                  <span className="min-w-[120px]">Participante {index + 1}</span>
                  <Select value={selectedModels[index]} onValueChange={(value: string) => handleModelChange(index, value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center p-4 border rounded-lg">
                <Bot className="h-8 w-8 mr-4 text-primary" />
                <div>
                  <h3 className="font-medium">Participantes LLM</h3>
                  <p className="text-sm text-muted-foreground">Modelos de IA compiten para resolver problemas</p>
                </div>
              </div>
              <div className="flex items-center p-4 border rounded-lg">
                <Code className="h-8 w-8 mr-4 text-primary" />
                <div>
                  <h3 className="font-medium">Desafíos de Programación</h3>
                  <p className="text-sm text-muted-foreground">Problemas reales de programación para resolver</p>
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button onClick={handleStartCompetition} className="w-full" size="lg" disabled={isLoading}>
              {isLoading ? "Cargando Problemas..." : "Iniciar Competencia"}
            </Button>
          </CardFooter>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-lg">Resultados en Tiempo Real</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Observa cómo los LLMs compiten en tiempo real para resolver desafíos de programación.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-lg">Múltiples Participantes</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Soporte para hasta 3 participantes LLM diferentes en cada competencia.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-lg">Tabla de Clasificación</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Seguimiento del rendimiento con una tabla de clasificación dinámica que muestra puntuaciones y rankings.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}
