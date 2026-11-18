const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("token", token);
  }
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expirée, veuillez vous reconnecter.");
  }

  if (!response.ok) {
    let errorDetail = "Une erreur est survenue";
    try {
      const errJson = await response.json();
      if (Array.isArray(errJson.detail)) {
        // Erreurs de validation FastAPI : [{ loc, msg, ... }]
        errorDetail = errJson.detail.map((d: any) => `${d.loc?.slice(-1)[0] ?? ""} : ${d.msg}`).join(" — ");
      } else {
        errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
      }
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    login: async (email: string, password: string) => {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Identifiants invalides");
      }
      return res.json() as Promise<{ access_token: string; token_type: string }>;
    },
    register: (data: { name: string; email: string; password: string; role: "teacher" | "student" }) =>
      request<{ access_token: string; token_type: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  users: {
    me: () => request<{ id: number; name: string; email: string; role: string; is_active: boolean }>("/users/me"),
    list: (role?: string) => request<any[]>(`/users${role ? `?role=${role}` : ""}`),
    create: (data: any) => request<any>("/users", { method: "POST", body: JSON.stringify(data) }),
  },

  groups: {
    list: () => request<any[]>("/groups"),
    get: (id: number) => request<any>(`/groups/${id}`),
    create: (name: string) => request<any>("/groups", { method: "POST", body: JSON.stringify({ name }) }),
    addStudents: (groupId: number, studentIds: number[]) =>
      request<any>(`/groups/${groupId}/students`, {
        method: "POST",
        body: JSON.stringify({ student_ids: studentIds }),
      }),
    removeStudent: (groupId: number, studentId: number) =>
      request<any>(`/groups/${groupId}/students/${studentId}`, { method: "DELETE" }),
    delete: (groupId: number) => request<void>(`/groups/${groupId}`, { method: "DELETE" }),
    regenerateCode: (groupId: number) =>
      request<any>(`/groups/${groupId}/regenerate-code`, { method: "POST" }),
    // Espace étudiant
    mine: () =>
      request<{ id: number; name: string; teacher_name: string; student_count: number }[]>("/groups/mine"),
    leave: (groupId: number) => request<void>(`/groups/${groupId}/leave`, { method: "POST" }),
    join: (code: string) =>
      request<{ group: { id: number; name: string; teacher_name: string; student_count: number }; new_exams: number }>(
        "/groups/join",
        { method: "POST", body: JSON.stringify({ code }) }
      ),
  },

  quizzes: {
    list: () => request<any[]>("/quizzes"),
    get: (id: number) => request<any>(`/quizzes/${id}`),
    create: (data: {
      specialty: string;
      subject: string;
      level: string;
      nb_questions: number;
      chapters?: string;
    }) => request<any>("/quizzes", { method: "POST", body: JSON.stringify(data) }),
    retry: (id: number) => request<any>(`/quizzes/${id}/retry`, { method: "POST" }),
    validate: (id: number) => request<any>(`/quizzes/${id}/validate`, { method: "POST" }),
    delete: (id: number) => request<void>(`/quizzes/${id}`, { method: "DELETE" }),
  },

  questions: {
    update: (id: number, data: any) =>
      request<any>(`/questions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/questions/${id}`, { method: "DELETE" }),
  },

  sessions: {
    list: () => request<any[]>("/sessions"),
    get: (id: number) => request<any>(`/sessions/${id}`),
    create: (data: {
      quiz_id: number;
      group_id: number;
      opens_at: string;
      closes_at: string;
      duration_minutes: number;
      questions_per_student: number;
      points_per_question?: number;
      scoring_rule?: string;
      penalty?: number;
    }) => request<any>("/sessions", { method: "POST", body: JSON.stringify(data) }),
    publish: (id: number) => request<any>(`/sessions/${id}/publish`, { method: "POST" }),
    delete: (id: number, force = false) =>
      request<void>(`/sessions/${id}${force ? "?force=true" : ""}`, { method: "DELETE" }),
    attempts: (id: number) => request<any[]>(`/sessions/${id}/attempts`),
    cancelQuestion: (sessionId: number, questionId: number) =>
      request<any>(`/sessions/${sessionId}/cancel-question/${questionId}`, { method: "POST" }),
    exportUrl: (id: number) => `${API_URL}/sessions/${id}/export`,
  },

  attempts: {
    myList: () => request<any[]>("/attempts/me"),
    getOrStart: (id: number) => request<any>(`/attempts/${id}`),
    saveAnswers: (id: number, answers: Record<number, number[]>) =>
      request<{ status: string; updated_at: string }>(`/attempts/${id}/answers`, {
        method: "PUT",
        body: JSON.stringify({ answers }),
      }),
    submit: (id: number) => request<any>(`/attempts/${id}/submit`, { method: "POST" }),
    getReview: (id: number) => request<any>(`/attempts/${id}/review`),
    grade: (id: number, data: { final_score: number; teacher_comment?: string }) =>
      request<any>(`/attempts/${id}/grade`, { method: "PATCH", body: JSON.stringify(data) }),
  },
};
