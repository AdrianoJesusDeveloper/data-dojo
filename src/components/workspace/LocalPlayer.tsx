interface LocalPlayerProps {
  src: string;
}

export function LocalPlayer({ src }: LocalPlayerProps) {
  return (
    <video
      src={src}
      controls
      preload="metadata"
      className="w-full h-full object-contain"
    />
  );
}