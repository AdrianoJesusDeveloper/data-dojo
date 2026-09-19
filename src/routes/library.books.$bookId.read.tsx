import { createFileRoute } from "@tanstack/react-router";
import BookReader from "@/pages/BookReader";
import { requireAdministrativeAccess } from "@/lib/admin-access";
export const Route = createFileRoute("/library/books/$bookId/read")({ beforeLoad: requireAdministrativeAccess, component: ReaderRoute });
function ReaderRoute() { const { bookId } = Route.useParams(); return <BookReader bookId={Number(bookId)} />; }
