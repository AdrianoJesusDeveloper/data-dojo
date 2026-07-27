import { ExerciseCard } from "./ExerciseCard";
import { CourseTree } from "./CourseTree";

interface LessonPlayerProps {
  course: any;
  currentLesson: any;
  setCurrentLesson: any;
  setCode: any;
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
}: LessonPlayerProps) {
  console.log("CURSO", course);
  console.log("LESSON ATUAL", currentLesson);

  const youtubeEmbed = getYoutubeEmbed(currentLesson?.video_url);

  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">

      <div className="aspect-video bg-black flex items-center justify-center">

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

      </div>

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