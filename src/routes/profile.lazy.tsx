import { createLazyFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';

export const Route = createLazyFileRoute('/profile')({
  component: ProfileComponent,
});

function ProfileComponent() {
  const [user, setUser] = useState<{ username: string; email: string; profile_picture: string | null; xp_points: number } | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Busca os dados atuais do aluno ao carregar a página
  useEffect(() => {
    fetch('https://data-dojo.onrender.com/api/user/profile/', {
      headers: {
        'Authorization': `Token ${localStorage.getItem('token')}`, // Ajuste conforme seu sistema de login
      }
    })
      .then(res => res.json())
      .then(data => {
        setUser(data);
        if (data.profile_picture) setPreviewUrl(data.profile_picture);
      })
      .catch(err => console.error("Erro ao carregar perfil:", err));
  }, []);

  // Trata a seleção do arquivo de imagem
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  // Envia a foto de perfil para o Django
  const handleSaveProfile = async () => {
    if (!selectedFile) return;
    setLoading(false);

    const formData = new FormData();
    formData.append('profile_picture', selectedFile);

    try {
      setLoading(true);
      const response = await fetch('https://data-dojo.onrender.com/api/user/profile/', {
        method: 'PATCH',
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
        },
        body: formData
      });

      if (response.ok) {
        alert('Perfil atualizado com sucesso!');
      } else {
        alert('Erro ao atualizar perfil.');
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d0e12] text-white p-8 font-sans">
      <div className="max-w-2xl mx-auto bg-[#14161d] rounded-xl p-8 border border-gray-800">
        <h1 className="text-3xl font-bold mb-2">Gerenciamento de Conta</h1>
        <p className="text-gray-400 mb-8">Personalize seu perfil no Data Driven Dojô</p>

        {/* Seção da Foto de Perfil */}
        <div className="flex items-center gap-6 mb-8 bg-[#1a1d26] p-6 rounded-lg border border-gray-800">
          <div className="relative w-24 h-24 rounded-full overflow-hidden bg-gray-700 border-2 border-[#ff3b30]">
            {previewUrl ? (
              <img src={previewUrl} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-gray-400">
                {user?.username?.substring(0, 2).toUpperCase() || 'U'}
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Foto do Avatar</label>
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#ff3b30] file:text-white hover:file:bg-red-600 cursor-pointer"
            />
          </div>
        </div>

        {/* Dados da Conta */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Nome de Usuário</label>
            <input type="text" value={user?.username || ''} disabled className="w-full bg-[#1a1d26] border border-gray-800 rounded-md p-3 text-gray-500 cursor-not-allowed" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">E-mail institucional</label>
            <input type="email" value={user?.email || ''} disabled className="w-full bg-[#1a1d26] border border-gray-800 rounded-md p-3 text-gray-500 cursor-not-allowed" />
          </div>
          <div className="pt-4 flex justify-end">
            <button 
              onClick={handleSaveProfile}
              disabled={loading || !selectedFile}
              className="bg-[#ff3b30] hover:bg-red-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded-md transition-colors"
            >
              {loading ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}