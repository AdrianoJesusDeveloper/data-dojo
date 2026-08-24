import { DojoHeader } from "@/components/DojoHeader";
import { BeltBadge, BeltProgress } from "@/components/BeltBadge";

import { useDojo, getCurrentBelt, BELTS, useHydrated, updateStudentName } from "@/lib/dojo-store";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

import { toast, Toaster } from "sonner";

import { celebratePromotion, celebrateXp } from "@/lib/celebrate";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { useEffect, useMemo, useState } from "react";



export default function Dashboard() {
  const { state, fastForward, reset } = useDojo();

  const hydrated = useHydrated();

  const belt = getCurrentBelt(state.xp);

  const [profile, setProfile] = useState<any>(null);

  /*
    Busca usuário autenticado
  */

  useEffect(() => {
    async function loadProfile() {
      const token = useAuthStore.getState().token;

      if (!token) return;

      try {
        const { data } = await api.get("/api/user/profile/");

        setProfile(data);

        if (data.username) {
          updateStudentName(data.username);
        }
      } catch (error) {
        console.error(error);
      }
    }

    loadProfile();
  }, []);

  const initials = profile?.username ? profile.username.substring(0, 2).toUpperCase() : "DD";

  const chartData = useMemo(() => {
    let total = 0;

    return state.history.map((item) => {
      total += item.xp;

      return {
        date: new Date(item.date).toLocaleDateString("pt-BR"),

        xp: item.xp,

        cumulative: total,
      };
    });
  }, [state.history]);

  if (!hydrated) {
    return (
      <>
        <DojoHeader />

        <div className="p-10">Carregando Dojô...</div>
      </>
    );
  }

  return (
    <div className="min-h-screen">
      <Toaster position="top-right" />

      <DojoHeader />

      <main
        className="
max-w-7xl
mx-auto
px-6
py-10
"
      >
        <section
          className="
flex
justify-between
items-center
gap-5
flex-wrap
"
        >
          <div>
            <p
              className="
text-xs
uppercase
tracking-widest
text-muted-foreground
"
            >
              Dashboard do Aluno
            </p>

            <h1 className="font-display font-extrabold text-4xl mt-1">
                Olá, Sensei {profile?.studentName || "Aprendiz"}
            </h1>

            <p
              className="
text-muted-foreground
mt-2
"
            >
              Seu caminho Kaizen rumo à maestria.
            </p>
          </div>

          <div
            className="
flex
items-center
gap-4
bg-card
border
rounded-xl
p-4
"
          >
            <div
              className="
w-16
h-16
rounded-full
overflow-hidden
border-4
flex
items-center
justify-center
font-bold
"
              style={{
                borderColor: belt.color,
              }}
            >
              {profile?.profile_picture ? (
                <img
                  src={profile.profile_picture}

                  className="
w-full
h-full
object-cover
"
                />
              ) : (
                initials
              )}
            </div>

            <div>
              <h3
                className="
font-bold
"
              >
                {profile?.username ?? state.studentName}
              </h3>

              <p
                className="
text-sm
text-muted-foreground
"
              >
                🥋 {belt.name}
              </p>

              <p
                className="
text-sm
text-orange-400
font-bold
"
              >
                ⭐ {state.xp} XP
              </p>

              <a
                href="/profile"

                className="
text-xs
text-blue-400
hover:underline
"
              >
                Gerenciar Perfil
              </a>
            </div>
          </div>
        </section>

        <section
          className="
grid
md:grid-cols-4
gap-5
mt-10
"
        >
          <KpiCard
            label="XP Kaizen"

            value={`${state.xp}`}

            accent="#FFA500"
          />

          <KpiCard
            label="Horas treinadas"

            value={`${state.hours}h`}

            accent="#0057B8"
          />

          <KpiCard
            label="Sequência"

            value={`${state.streak} dias`}

            accent="#E63946"
          />

          <div
            className="
rounded-xl
border
bg-card
p-5
"
          >
            <p
              className="
text-xs
uppercase
text-muted-foreground
"
            >
              Faixa Atual
            </p>

            <div className="mt-3">
              <BeltBadge belt={belt} />
            </div>
          </div>
        </section>

        <section
          className="
mt-8
rounded-xl
border
bg-card
p-6
"
        >
          <h2
            className="
text-xl
font-bold
mb-5
"
          >
            Graduação Kaizen
          </h2>

          <BeltProgress xp={state.xp} />
        </section>

        <section
          className="
mt-8
grid
lg:grid-cols-2
gap-5
"
        >
          <ChartCard title="Evolução XP">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <CartesianGrid stroke="#333" />

                <XAxis dataKey="date" />

                <YAxis />

                <Tooltip />

                <Area
                  dataKey="cumulative"

                  stroke="#FFA500"

                  fill="#FFA500"
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Conquistas">
            <div
              className="
grid
grid-cols-2
gap-4
"
            >
              {BELTS.map((b) => (
                <div
                  key={b.id}

                  className="
border
rounded-lg
p-4
"
                >
                  <div
                    className="
font-bold
"
                  >
                    {b.name}
                  </div>

                  <p
                    className="
text-xs
text-muted-foreground
"
                  >
                    {b.minXp} XP
                  </p>
                </div>
              ))}
            </div>
          </ChartCard>
        </section>
      </main>
    </div>
  );
}

function KpiCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div
      className="
rounded-xl
border
bg-card
p-5
"
    >
      <p
        className="
text-xs
uppercase
text-muted-foreground
"
      >
        {label}
      </p>

      <h2
        className="
text-3xl
font-black
mt-3
"

        style={{
          color: accent,
        }}
      >
        {value}
      </h2>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="
rounded-xl
border
bg-card
p-6
"
    >
      <h2
        className="font-bold
text-xl
mb-4
"
      >
        {title}
      </h2>

      {children}
    </div>
  );
}
