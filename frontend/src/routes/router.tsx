import { createBrowserRouter } from "react-router";
import { AppLayout } from "../components/AppLayout";
import { LoginPage } from "../pages/LoginPage";
import { MyTicketsPage } from "../pages/MyTicketsPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { QueuePage } from "../pages/QueuePage";
import { RegisterPage } from "../pages/RegisterPage";
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
