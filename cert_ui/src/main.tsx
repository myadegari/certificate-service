import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

import { BrowserRouter } from "react-router";
import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import AuthenticationProvider from "@/context/authenticationContext";

// Create a client
import App from './App.tsx';



const queryClient = new QueryClient()
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
    <AuthenticationProvider>
    <App />
    </AuthenticationProvider>
  </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
