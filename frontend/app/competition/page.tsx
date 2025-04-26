"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, Clock, Trophy, Code, AlertCircle } from "lucide-react"

interface Problem {
  problem_id: string
  problem_name: string
}

interface ProblemStatus {
  attempts: number
  accepted: boolean
  acceptedAt?: number // Timestamp when the problem was accepted
}

interface Participant {
  id: string
  model: string
  score: number
  problemStatus: Record<string, ProblemStatus>
  isProcessing: boolean
  currentProblem?: string
  penalty: number // Total penalty time in milliseconds
}

// Actualizar la interfaz Submission para incluir todos los estados de veredicto
interface Submission {
  id: string
  participantId: string
  model: string
  problemId: string
  status:
    | "QUEUED"
    | "PROCESSING"
    | "ACCEPTED"
    | "WRONG_ANSWER"
    | "TIME_LIMIT"
    | "MEMORY_LIMIT"
    | "COMPILATION_ERROR"
    | "RUNTIME_ERROR"
    | "OTHER"
  runtimeErrorDetail?: string // Para almacenar el detalle específico del error de tiempo de ejecución
  timestamp: number
  testCases?: TestCase[]
}

interface TestCase {
  test_case: string
  expected_output: string
  actual_output: string
  status: "aceptado" | "error"
}

export default function CompetitionPage() {
  const searchParams = useSearchParams()
  const [problems, setProblems] = useState<Problem[]>([])
  const [participants, setParticipants] = useState<Participant[]>([])
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [timeRemaining, setTimeRemaining] = useState(300) // 5 minutes in seconds
  const [isCompetitionActive, setIsCompetitionActive] = useState(true)
  const [competitionStartTime, setCompetitionStartTime] = useState(Date.now())
  const submissionsContainerRef = useRef<HTMLDivElement>(null)

  // Initialize competition data from URL params
  useEffect(() => {
    try {
      // Get problems from URL
      const problemsParam = searchParams.get("problems")
      const parsedProblems: Problem[] = problemsParam ? JSON.parse(decodeURIComponent(problemsParam)) : []

      // Get participants data from URL
      const modelsParam = searchParams.get("models")
      const parsedParticipantsData = modelsParam ? JSON.parse(decodeURIComponent(modelsParam)) : []

      // Set competition start time
      setCompetitionStartTime(Date.now())

      // Initialize participants with problem statuses
      const initializedParticipants = parsedParticipantsData.map((p: { id: string; model: string }) => {
        const problemStatus: Record<string, ProblemStatus> = {}
        parsedProblems.forEach((problem) => {
          problemStatus[problem.problem_id] = {
            attempts: 0,
            accepted: false,
          }
        })

        return {
          ...p,
          score: 0,
          problemStatus,
          isProcessing: false,
          penalty: 0,
        }
      })

      setProblems(parsedProblems)
      setParticipants(initializedParticipants)
      setIsLoading(false)
    } catch (error) {
      console.error("Error parsing URL parameters:", error)
      setIsLoading(false)
    }
  }, [searchParams])

  // Timer countdown
  useEffect(() => {
    if (!isCompetitionActive || timeRemaining <= 0) return

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          setIsCompetitionActive(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isCompetitionActive, timeRemaining])

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  // Format penalty time as HH:MM:SS.mmm
  const formatPenaltyTime = (milliseconds: number) => {
    const hours = Math.floor(milliseconds / 3600000)
    const minutes = Math.floor((milliseconds % 3600000) / 60000)
    const seconds = Math.floor((milliseconds % 60000) / 1000)
    const ms = milliseconds % 1000

    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.${ms.toString().padStart(3, "0")}`
  }

  // Calculate score for a participant
  const calculateScore = (participant: Participant) => {
    return Object.values(participant.problemStatus).filter((status) => status.accepted).length
  }

  // Generate leaderboard data
  const getLeaderboard = useCallback(() => {
    return [...participants]
      .map((p) => ({
        ...p,
        score: calculateScore(p),
      }))
      .sort((a, b) => {
        // Sort by score (descending)
        if (b.score !== a.score) return b.score - a.score

        // If scores are tied, sort by penalty time (ascending)
        return a.penalty - b.penalty
      })
  }, [participants])

  // Process a participant's turn
  const processTurn = useCallback(
    async (participant: Participant) => {
      if (!isCompetitionActive || participant.isProcessing) return

      // Find a problem that hasn't been accepted yet
      const unsolvedProblems = problems.filter((problem) => !participant.problemStatus[problem.problem_id].accepted)

      // If all problems are solved, don't make any more submissions
      if (unsolvedProblems.length === 0) {
        setParticipants((prev) =>
          prev.map((p) =>
            p.id === participant.id ? { ...p, isProcessing: false, currentProblem: undefined } : p,
          ),
        )
        return
      }

      // Randomly select an unsolved problem
      const selectedProblem = unsolvedProblems[Math.floor(Math.random() * unsolvedProblems.length)]

      // Update participant status
      setParticipants((prev) =>
        prev.map((p) =>
          p.id === participant.id ? { ...p, isProcessing: true, currentProblem: selectedProblem.problem_id } : p,
        ),
      )

      // Create a submission in progress
      const submissionId = `sub-${Date.now()}-${participant.id}`
      const newSubmission: Submission = {
        id: submissionId,
        participantId: participant.id,
        model: participant.model,
        problemId: selectedProblem.problem_id,
        status: "QUEUED",
        timestamp: Date.now(),
      }

      setSubmissions((prev) => [newSubmission, ...prev].slice(0, 20)) // Keep only the 20 most recent submissions

      try {
        // Prepare leaderboard status for API
        const leaderboardStatus = participants.reduce(
          (acc, p) => {
            acc[p.id] = Object.entries(p.problemStatus).reduce(
              (problemAcc, [problemId, status]) => {
                problemAcc[problemId] = status.accepted ? "aceptado" : status.attempts
                return problemAcc
              },
              {} as Record<string, string | number>,
            )
            return acc
          },
          {} as Record<string, Record<string, string | number>>,
        )

        // Make API request
        const response = (await Promise.race([
          fetch("http://localhost:8080/api/code_generation", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              contestant_id: participant.id,
              model: participant.model,
              problem_id: selectedProblem.problem_id,
              leaderboard: leaderboardStatus,
            }),
          }),
          new Promise(
            (_, reject) => setTimeout(() => reject(new Error("Tiempo excedido")), 240000), // 2 minute timeout
          ),
        ])) as Response

        if (!response.ok) {
          throw new Error(`Error en la solicitud: ${response.status}`)
        }

        const result = await response.json()
        const verdict = result.verdict

        // Procesar el estado del veredicto
        let submissionStatus: Submission["status"] = "OTHER"
        let runtimeErrorDetail: string | undefined = undefined

        if (verdict.status === "ACCEPTED") {
          submissionStatus = "ACCEPTED"
        } else if (verdict.status === "WRONG_ANSWER") {
          submissionStatus = "WRONG_ANSWER"
        } else if (verdict.status === "TIME_LIMIT") {
          submissionStatus = "TIME_LIMIT"
        } else if (verdict.status === "MEMORY_LIMIT") {
          submissionStatus = "MEMORY_LIMIT"
        } else if (verdict.status === "COMPILATION_ERROR") {
          submissionStatus = "COMPILATION_ERROR"
        } else if (verdict.status === "QUEUED") {
          submissionStatus = "QUEUED"
        } else if (verdict.status === "PROCESSING") {
          submissionStatus = "PROCESSING"
        } else if (verdict.status.startsWith("RUNTIME_ERROR")) {
          submissionStatus = "RUNTIME_ERROR"
          runtimeErrorDetail = verdict.status.replace("RUNTIME_ERROR_", "")
        }

        setSubmissions((prev) =>
          prev.map((sub) =>
            sub.id === submissionId
              ? {
                  ...sub,
                  status: submissionStatus,
                  runtimeErrorDetail,
                  testCases: result.test_cases,
                }
              : sub,
          ),
        )

        // Actualizar el estado del problema del participante
        setParticipants((prev) =>
          prev.map((p) => {
            if (p.id !== participant.id) return p

            const updatedProblemStatus = { ...p.problemStatus }
            const currentTime = Date.now()
            const wasAlreadyAccepted = updatedProblemStatus[selectedProblem.problem_id].accepted

            updatedProblemStatus[selectedProblem.problem_id] = {
              attempts: updatedProblemStatus[selectedProblem.problem_id].attempts + 1,
              accepted: submissionStatus === "ACCEPTED" || wasAlreadyAccepted,
              // Only update acceptedAt if it wasn't already accepted and is now accepted
              acceptedAt:
                submissionStatus === "ACCEPTED" && !wasAlreadyAccepted
                  ? currentTime
                  : updatedProblemStatus[selectedProblem.problem_id].acceptedAt,
            }

            // Calculate new penalty
            let newPenalty = p.penalty
            if (submissionStatus === "ACCEPTED" && !wasAlreadyAccepted) {
              // Add penalty for this problem (time since competition start)
              const problemPenalty = currentTime - competitionStartTime
              newPenalty += problemPenalty
            }

            return {
              ...p,
              isProcessing: false,
              currentProblem: undefined,
              problemStatus: updatedProblemStatus,
              score: Object.values(updatedProblemStatus).filter((status) => status.accepted).length,
              penalty: newPenalty,
            }
          }),
        )
      } catch (error) {
        console.error("Error processing turn:", error)

        // Actualizar el envío con error
        setSubmissions((prev) =>
          prev.map((sub) =>
            sub.id === submissionId
              ? {
                  ...sub,
                  status: error instanceof Error && error.message === "Tiempo excedido" ? "TIME_LIMIT" : "OTHER",
                }
              : sub,
          ),
        )

        // Reset participant processing status
        setParticipants((prev) =>
          prev.map((p) => (p.id === participant.id ? { ...p, isProcessing: false, currentProblem: undefined } : p)),
        )
      }
    },
    [isCompetitionActive, participants, problems, competitionStartTime],
  )

  // Process turns for all participants in a loop
  useEffect(() => {
    if (!isCompetitionActive || isLoading) return

    let isProcessing = false

    const processTurns = async () => {
      if (isProcessing) return
      isProcessing = true

      try {
        for (const participant of participants) {
          if (!participant.isProcessing) {
            await processTurn(participant)
          }
        }
      } finally {
        isProcessing = false
      }
    }

    const interval = setInterval(processTurns, 1000) // Check every second

    return () => clearInterval(interval)
  }, [isCompetitionActive, isLoading, participants, processTurn])

  // Render status cell for leaderboard
  const renderStatusCell = (status: ProblemStatus) => {
    if (status.accepted) {
      return (
        <div className="bg-green-100 text-green-800 font-medium rounded-md px-2 py-1 text-center">
          +{status.attempts}
        </div>
      )
    } else if (status.attempts > 0) {
      return (
        <div className="bg-red-100 text-red-800 font-medium rounded-md px-2 py-1 text-center">{status.attempts}</div>
      )
    } else {
      return <div className="bg-gray-100 text-gray-500 rounded-md px-2 py-1 text-center">-</div>
    }
  }

  // Reemplazar la función renderStatusBadge con esta versión actualizada
  const renderStatusBadge = (status: Submission["status"], runtimeErrorDetail?: string) => {
    switch (status) {
      case "QUEUED":
        return (
          <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-200">
            En cola
          </Badge>
        )
      case "PROCESSING":
        return (
          <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-200">
            Procesando
          </Badge>
        )
      case "ACCEPTED":
        return (
          <Badge variant="outline" className="bg-green-100 text-green-800 border-green-200">
            Aceptado
          </Badge>
        )
      case "WRONG_ANSWER":
        return (
          <Badge variant="outline" className="bg-red-100 text-red-800 border-red-200">
            Respuesta incorrecta
          </Badge>
        )
      case "TIME_LIMIT":
        return (
          <Badge variant="outline" className="bg-orange-100 text-orange-800 border-orange-200">
            Límite de tiempo
          </Badge>
        )
      case "MEMORY_LIMIT":
        return (
          <Badge variant="outline" className="bg-purple-100 text-purple-800 border-purple-200">
            Límite de memoria
          </Badge>
        )
      case "COMPILATION_ERROR":
        return (
          <Badge variant="outline" className="bg-pink-100 text-pink-800 border-pink-200">
            Error de compilación
          </Badge>
        )
      case "RUNTIME_ERROR":
        return (
          <Badge variant="outline" className="bg-indigo-100 text-indigo-800 border-indigo-200">
            Error de ejecución {runtimeErrorDetail ? `(${runtimeErrorDetail})` : ""}
          </Badge>
        )
      case "OTHER":
        return (
          <Badge variant="outline" className="bg-gray-100 text-gray-800 border-gray-200">
            Otro error
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="bg-gray-100 text-gray-800 border-gray-200">
            Desconocido
          </Badge>
        )
    }
  }

  // Effect to handle submission animations
  useEffect(() => {
    if (submissionsContainerRef.current) {
      // Scroll to bottom when new submissions are added
      submissionsContainerRef.current.scrollTop = submissionsContainerRef.current.scrollHeight
    }
  }, [submissions])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Cargando competición...</h2>
          <p className="text-muted-foreground">Configurando el entorno de la competición</p>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-4 md:p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <Link href="/">
              <Button variant="outline" size="sm" className="mb-2">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Volver al inicio
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Competición de Programación LLM</h1>
            <p className="text-muted-foreground">
              {participants.length} participantes compitiendo en {problems.length} problemas
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Clock className="h-5 w-5 text-orange-500" />
              <span className={timeRemaining < 60 ? "text-red-500" : ""}>
                Tiempo restante: {formatTime(timeRemaining)}
              </span>
            </div>
            <Progress value={(timeRemaining / 300) * 100} className="w-40 h-2" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 w-full">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xl font-bold flex items-center">
                  <Trophy className="h-5 w-5 text-yellow-500 mr-2" />
                  Tabla de Clasificación
                </CardTitle>
                <Badge variant={isCompetitionActive ? "default" : "secondary"} className="ml-2">
                  {isCompetitionActive ? "En curso" : "Finalizada"}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted">
                        <TableHead className="font-bold">Pos</TableHead>
                        <TableHead className="font-bold">Participante</TableHead>
                        <TableHead className="font-bold">Modelo</TableHead>
                        <TableHead className="font-bold text-center">Resueltos</TableHead>
                        <TableHead className="font-bold text-center">Penalización</TableHead>
                        {problems.map((problem) => (
                          <TableHead key={problem.problem_id} className="font-bold text-center">
                            {problem.problem_id}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {getLeaderboard().map((participant, index) => (
                        <TableRow key={participant.id} className={participant.isProcessing ? "bg-yellow-50" : ""}>
                          <TableCell className="font-medium">
                            {index === 0 ? (
                              <span className="inline-flex items-center justify-center w-6 h-6 bg-yellow-100 text-yellow-800 rounded-full font-bold">
                                1
                              </span>
                            ) : (
                              index + 1
                            )}
                          </TableCell>
                          <TableCell className="font-medium">
                            {participant.id}
                            {participant.isProcessing && (
                              <span className="ml-2 inline-block w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span>
                            )}
                          </TableCell>
                          <TableCell>{participant.model}</TableCell>
                          <TableCell className="text-center font-bold">{participant.score}</TableCell>
                          <TableCell className="text-center">
                            {participant.penalty > 0 ? formatPenaltyTime(participant.penalty) : "-"}
                          </TableCell>
                          {problems.map((problem) => (
                            <TableCell key={`${participant.id}-${problem.problem_id}`} className="p-1">
                              {renderStatusCell(participant.problemStatus[problem.problem_id])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xl font-bold flex items-center">
                  <Code className="h-5 w-5 text-blue-500 mr-2" />
                  Envíos Recientes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  ref={submissionsContainerRef}
                  className="space-y-4 max-h-[600px] overflow-y-auto pr-2 flex flex-col-reverse"
                  style={{ scrollBehavior: "smooth" }}
                >
                  {submissions.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground flex flex-col items-center">
                      <AlertCircle className="h-8 w-8 mb-2" />
                      <p>No hay envíos todavía</p>
                    </div>
                  ) : (
                    [...submissions].reverse().map((submission, index) => (
                      <div
                        key={submission.id}
                        className={`p-3 rounded-lg border transition-all duration-300 transform ${
                          submission.status === "PROCESSING" || submission.status === "QUEUED"
                            ? "border-yellow-200 bg-yellow-50"
                            : submission.status === "ACCEPTED"
                              ? "border-green-200 bg-green-50"
                              : "border-red-200 bg-red-50"
                        }`}
                        style={{
                          animationName: "slideUp",
                          animationDuration: "0.3s",
                          animationFillMode: "both",
                          animationDelay: `${index * 0.05}s`,
                        }}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="font-medium">{submission.participantId}</p>
                            <p className="text-sm text-muted-foreground">Problema {submission.problemId}</p>
                          </div>
                          {renderStatusBadge(submission.status, submission.runtimeErrorDetail)}
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Modelo: {submission.model}</span>
                          <span>
                            {new Date(submission.timestamp).toLocaleTimeString("es-ES", {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        </div>

                        {submission.testCases && submission.testCases.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-dashed border-gray-200">
                            <p className="text-xs font-medium mb-1">
                              Casos de prueba: {submission.testCases.filter((tc) => tc.status === "aceptado").length}/
                              {submission.testCases.length}
                            </p>
                            <div className="flex gap-1">
                              {submission.testCases.map((tc, idx) => (
                                <div
                                  key={idx}
                                  className={`w-2 h-2 rounded-full ${tc.status === "aceptado" ? "bg-green-500" : "bg-red-500"}`}
                                  title={`Caso ${idx + 1}: ${tc.status}`}
                                ></div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <style jsx global>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </main>
  )
}
