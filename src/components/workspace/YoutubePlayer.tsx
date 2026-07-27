interface YoutubePlayerProps {
  url: string;
}

function getYoutubeEmbedUrl(url: string) {
  try {
    const parsed = new URL(url);

    if (parsed.hostname.includes("youtu.be")) {
      const id = parsed.pathname.slice(1);
      return `https://www.youtube.com/embed/${id}`;
    }

    if (parsed.hostname.includes("youtube.com")) {
      const id = parsed.searchParams.get("v");
      if (id) {
        return `https://www.youtube.com/embed/${id}`;
      }
    }
  } catch {}

  return "";
}

export function YoutubePlayer({ url }: YoutubePlayerProps) {
  const embed = getYoutubeEmbedUrl(url);

  if (!embed) {
    return (
      <div className="flex items-center justify-center h-full text-white">
        URL do YouTube inválida.
      </div>
    );
  }

  return (
    <iframe
      src={embed}
      title="Video"
      className="w-full h-full"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
    />
  );
}