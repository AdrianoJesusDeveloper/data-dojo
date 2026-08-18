import { useEffect, useState } from "react";

import { api } from "../lib/api";

interface UserProfile {
  username: string;
  email: string;
  profile_picture: string | null;
  xp_points: number;
}

export default function ProfileComponent() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [username, setUsername] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    api
      .get<UserProfile>("/api/user/profile/")
      .then(({ data }) => {
        if (!active) return;
        setUser(data);
        setUsername(data.username);
        setPreviewUrl(data.profile_picture);
      })
      .catch((error) => console.error("Erro ao carregar perfil:", error));

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleSaveProfile = async () => {
    setLoading(true);

    try {
      const formData = new FormData();
      if (selectedFile) formData.append("profile_picture", selectedFile);
      if (username !== user?.username) formData.append("username", username);

      const { data } = await api.patch<UserProfile>(
        "/api/user/profile/",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );

      setUser(data);
      setUsername(data.username);
      setSelectedFile(null);
      setPreviewUrl(data.profile_picture);
      window.alert("Perfil atualizado com sucesso!");
    } catch (error) {
      console.error("Erro ao atualizar perfil:", error);
      window.alert("Erro ao atualizar perfil.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d0e12] p-8 font-sans text-white">
      <div className="mx-auto max-w-2xl rounded-xl border border-gray-800 bg-[#14161d] p-8">
        <h1 className="mb-2 text-3xl font-bold">Gerenciamento de Conta</h1>
        <p className="mb-8 text-gray-400">
          Personalize seu perfil no Data Driven Dojô.
        </p>

        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-gray-800 bg-[#1a1d26] p-4">
            <p className="text-sm text-gray-400">🥋 Graduação</p>
            <p className="text-xl font-bold text-orange-400">Aluno</p>
          </div>
          <div className="rounded-lg border border-gray-800 bg-[#1a1d26] p-4">
            <p className="text-sm text-gray-400">⭐ Pontos Kaizen</p>
            <p className="text-xl font-bold text-orange-400">
              {user?.xp_points || 0} XP
            </p>
          </div>
          <div className="rounded-lg border border-gray-800 bg-[#1a1d26] p-4">
            <p className="text-sm text-gray-400">🔥 Jornada</p>
            <p className="text-xl font-bold text-orange-400">Data Driven Dojô</p>
          </div>
        </div>

        <div className="mb-8 flex items-center gap-6 rounded-lg border border-gray-800 bg-[#1a1d26] p-6">
          <div className="relative h-24 w-24 overflow-hidden rounded-full border-2 border-[#ff3b30] bg-gray-700">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="Avatar"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-2xl font-bold text-gray-400">
                {user?.username?.substring(0, 2).toUpperCase() || "U"}
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Foto do Avatar
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-400 file:mr-4 file:rounded-md file:border-0 file:bg-[#ff3b30] file:px-4 file:py-2 file:font-semibold file:text-white"
            />
          </div>
        </div>

        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-400">
            Nome de Usuário
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1 w-full rounded-md border border-gray-800 bg-[#1a1d26] p-3 text-white"
            />
          </label>

          <label className="block text-sm font-medium text-gray-400">
            E-mail institucional
            <input
              type="email"
              value={user?.email || ""}
              disabled
              className="mt-1 w-full cursor-not-allowed rounded-md border border-gray-800 bg-[#1a1d26] p-3 text-gray-500"
            />
          </label>

          <div className="flex justify-end pt-4">
            <button
              onClick={handleSaveProfile}
              disabled={loading || (!selectedFile && username === user?.username)}
              className="rounded-md bg-[#ff3b30] px-6 py-3 font-bold text-white transition-colors hover:bg-red-600 disabled:cursor-not-allowed disabled:bg-gray-700"
            >
              {loading ? "Salvando..." : "Salvar Alterações"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
