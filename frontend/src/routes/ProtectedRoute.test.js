// frontend/src/routes/ProtectedRoute.test.js
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import * as auth from "../services/auth";

jest.mock("../services/auth"); // replaces the whole module with auto-mocked functions

function renderWithRouter(initialPath = "/dashboard") {
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/auth" element={<div>Auth Page</div>} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Secret Dashboard</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

test("renders children when authenticated", () => {
  auth.isAuthenticated.mockReturnValue(true);
  renderWithRouter();
  expect(screen.getByText("Secret Dashboard")).toBeInTheDocument();
});

test("redirects to /auth when not authenticated", () => {
  auth.isAuthenticated.mockReturnValue(false);
  renderWithRouter();
  expect(screen.getByText("Auth Page")).toBeInTheDocument();
  expect(screen.queryByText("Secret Dashboard")).not.toBeInTheDocument();
});