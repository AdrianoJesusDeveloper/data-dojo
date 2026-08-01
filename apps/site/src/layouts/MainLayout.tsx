import { Outlet } from "@tanstack/react-router";
import Navbar from "../components/Navbar";

export default function MainLayout(){

  return (
    <>
      <Navbar />

      <main>
        <Outlet />
      </main>

    </>
  );
}