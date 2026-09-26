import { createBrowserRouter } from "react-router";
import { AppLayout } from "../components/AppLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { MyTicketsPage } from "../pages/MyTicketsPage";
import { NewTicketPage } from "../pages/NewTicketPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { QueuePage } from "../pages/QueuePage";
import { RegisterPage } from "../pages/RegisterPage";
import { TicketDetailPage } from "../pages/TicketDetailPage";
import { HomeRedirect, RequireAuth, RequireRole } from "./guards";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <HomeRedirect /> },
          { path: "tickets", element: <MyTicketsPage /> },
          { path: "tickets/new", element: <NewTicketPage /> },
          { path: "tickets/:id", element: <TicketDetailPage /> },
          {
            element: <RequireRole roles={["ADMIN"]} />,
            children: [{ path: "dashboard", element: <DashboardPage /> }],
          },
          {
            element: <RequireRole roles={["TECHNICIAN", "ADMIN"]} />,
            children: [{ path: "queue", element: <QueuePage /> }],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
