import { createBrowserRouter, type RouteObject } from "react-router";
import { AppLayout } from "../components/AppLayout";
import { LoginPage } from "../pages/LoginPage";
import { MyTicketsPage } from "../pages/MyTicketsPage";
import { NewTicketPage } from "../pages/NewTicketPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { QueuePage } from "../pages/QueuePage";
import { RegisterPage } from "../pages/RegisterPage";
import { RouteErrorPage } from "../pages/RouteErrorPage";
import { TicketDetailPage } from "../pages/TicketDetailPage";
import { HomeRedirect, RequireAuth, RequireRole } from "./guards";

/** Route table, shared by the browser router and the page tests (memory router). */
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage />, errorElement: <RouteErrorPage /> },
  { path: "/register", element: <RegisterPage />, errorElement: <RouteErrorPage /> },
  {
    element: <RequireAuth />,
    errorElement: <RouteErrorPage />,
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
            children: [
              // Admin-only screens are split into their own chunks: most people never
              // open them, so they don't download that code.
              {
                path: "dashboard",
                lazy: async () => ({
                  Component: (await import("../pages/DashboardPage")).DashboardPage,
                }),
              },
              {
                path: "admin",
                lazy: async () => ({ Component: (await import("../pages/AdminPage")).AdminPage }),
              },
            ],
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
];

export const router = createBrowserRouter(routes);
