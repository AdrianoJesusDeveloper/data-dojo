import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { toast } from "sonner";
import { ExerciseCard } from "./ExerciseCard";
import { CourseTree } from "./CourseTree";

interface LessonPlayerProps {
  course: any;
  currentLesson: any;
  setCurrentLesson: any;
  setCode: any;
  accessType: "enrollment" | "administrative" | "none";
  onCourseProgressChange: (percentage: string) => void;
}

interface LessonProgressResponse {
  status: "not_started" | "in_progress" | "completed";
  course_progress_percentage: string;
}

function getYoutubeEmbed(url?: string) {
  if (!url) return null;

  // https://youtu.be/xxxxxxxx
  const short = url.match(/youtu\.be\/([^?]+)/);
  if (short) {
    return `https://www.youtube.com/embed/${short[1]}`;
  }

  // https://www.youtube.com/watch?v=xxxxxxxx
  const watch = url.match(/[?&]v=([^&]+)/);
  if (watch) {
    return `https://www.youtube.com/embed/${watch[1]}`;
  }

  // já está em formato embed
  if (url.includes("/embed/")) {
    return url;
  }

  return null;
}

export function LessonPlayer({
  course,
  currentLesson,
  setCurrentLesson,
  setCode,
  accessType,
  onCourseProgressChange,
}: LessonPlayerProps) {
  const [lessonProgress, setLessonProgress] = useState<LessonProgressResponse | null>(null);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState(false);

  useEffect(() => {
    if (accessType !== "enrollment" || !currentLesson?.id) {
      setLessonProgress(null);
      setActivityError(false);
      return;
    }

    let active = true;
    setActivityLoading(true);
    setActivityError(false);
    api.post<LessonProgressResponse>(
      `/api/lesson-progress/by-lesson/${currentLesson.id}/start/`,
      {},
    ).then((response) => {
      if (!active) return;
      setLessonProgress(response.data);
      onCourseProgressChange(response.data.course_progress_percentage);
    }).catch(() => {
      if (!active) return;
      setActivityError(true);
      toast.error("Não foi possível registrar o início da aula.");
    }).finally(() => {
      if (active) setActivityLoading(false);
    });
    return () => { active = false; };
  }, [accessType, currentLesson?.id]);

  const completeLesson = async () => {
    if (!currentLesson?.id || activityLoading || lessonProgress?.status === "completed") return;
    setActivityLoading(true);
    setActivityError(false);
    try {
      const response = await api.post<LessonProgressResponse>(
        `/api/lesson-progress/by-lesson/${currentLesson.id}/complete/`,
        {},
      );
      setLessonProgress(response.data);
      onCourseProgressChange(response.data.course_progress_percentage);
      toast.success("Aula concluída.");
    } catch {
      setActivityError(true);
      toast.error("Não foi possível concluir a aula.");
    } finally {
      setActivityLoading(false);
    }
  };

  const youtubeEmbed = getYoutubeEmbed(currentLesson?.video_url);
  const isArticle = currentLesson?.content_type === "ARTICLE";

  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">

      {!isArticle && <div className="aspect-video bg-black flex items-center justify-center">

        {youtubeEmbed ? (

          <iframe
            src={youtubeEmbed}
            title={currentLesson?.title}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />

        ) : currentLesson?.file_upload ? (

          <video
            src={currentLesson.file_upload}
            controls
            preload="metadata"
            className="w-full h-full object-contain"
            onLoadStart={() => console.log("LOAD START")}
            onLoadedMetadata={() => console.log("METADATA")}
            onCanPlay={() => console.log("CAN PLAY")}
            onPlay={() => console.log("PLAY")}
            onError={(e) => {
              console.log("VIDEO ERROR");
              console.log(e.currentTarget.error);
              console.log("SRC:", e.currentTarget.currentSrc);
            }}
          />

        ) : (

          <div className="text-muted-foreground text-sm font-mono">
            Nenhum vídeo disponível.
          </div>

        )}

      </div>}

      <div className="p-6 overflow-y-auto">

        <div className="text-xs uppercase tracking-widest text-muted-foreground">
          Curso: {course?.title || "Sem curso selecionado"}
        </div>

        <h1 className="font-display font-bold text-2xl mt-1">
          {currentLesson?.title || "Nenhuma lição encontrada"}
        </h1>

        <p className="mt-3 text-sm text-muted-foreground">
          {course?.description}
        </p>

        {isArticle && (
          <article aria-label="Material didático" className="mt-6 min-w-0 space-y-4 break-words text-sm leading-7 [&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-bold [&_h4]:font-semibold [&_h5]:font-semibold [&_h6]:font-semibold [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-6 [&_ol]:pl-6 [&_li]:my-1 [&_a]:text-kaizen [&_a]:underline [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:font-mono [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-4 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4">
            {currentLesson.body?.trim() ? (
              <Markdown skipHtml components={{ a: ({ href, children }) => href ? <a href={href}>{children}</a> : <span>{children}</span> }}>
                {currentLesson.body}
              </Markdown>
            ) : (
              <p className="text-muted-foreground">Material desta aula ainda não disponível.</p>
            )}
          </article>
        )}

        {accessType === "enrollment" && (
          <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-border bg-background p-3 text-sm">
            <span>
              {activityLoading && !lessonProgress
                ? "Registrando início..."
                : activityError
                  ? "Atividade não registrada"
                  : lessonProgress?.status === "completed"
                    ? "Aula concluída"
                    : "Aula em andamento"}
            </span>
            <button
              type="button"
              onClick={completeLesson}
              disabled={activityLoading || activityError || lessonProgress?.status === "completed"}
              className="rounded bg-kaizen px-3 py-2 font-bold text-kaizen-foreground disabled:opacity-50"
            >
              {lessonProgress?.status === "completed" ? "Concluída" : "Marcar como concluída"}
            </button>
          </div>
        )}

        {currentLesson?.exercise && (
          <ExerciseCard exercise={currentLesson.exercise} />
        )}

        <CourseTree
          course={course}
          currentLesson={currentLesson}
          setCurrentLesson={setCurrentLesson}
          setCode={setCode}
        />

      </div>

    </section>
  );
}
