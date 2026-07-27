import { YoutubePlayer } from "./YoutubePlayer";
import { LocalPlayer } from "./LocalPlayer";

interface Props {
  lesson: any;
}

export function VideoPlayer({ lesson }: Props) {
  if (!lesson) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Nenhuma aula selecionada.
      </div>
    );
  }

  if (
    lesson.video_url &&
    (
      lesson.video_url.includes("youtube.com") ||
      lesson.video_url.includes("youtu.be")
    )
  ) {
    return <YoutubePlayer url={lesson.video_url} />;
  }

  if (lesson.file_upload) {
    return <LocalPlayer src={lesson.file_upload} />;
  }

  return (
    <div className="flex items-center justify-center h-full text-muted-foreground">
      Nenhum vídeo disponível.
    </div>
  );
}