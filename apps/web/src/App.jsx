import { useEffect, useState } from "react";

function App() {
  const [courses, setCourses] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/courses/")
      .then((response) => {
        if (!response.ok) throw new Error("Erro ao carregar cursos");
        return response.json();
      })
      .then(setCourses)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Data Driven Dojo</h1>
      <p>Lista de cursos disponíveis:</p>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {courses.length === 0 && !error ? (
        <p>Nenhum curso encontrado.</p>
      ) : (
        <ul>
          {courses.map((course) => (
            <li key={course.id} style={{ marginBottom: "1rem" }}>
              <strong>{course.title}</strong>
              <p>{course.description}</p>
              {course.modules?.length > 0 && (
                <div style={{ marginLeft: "1rem" }}>
                  <h4>Módulos:</h4>
                  <ul>
                    {course.modules.map((module) => (
                      <li key={module.id}>
                        {module.title} ({module.lessons.length} aulas)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;
