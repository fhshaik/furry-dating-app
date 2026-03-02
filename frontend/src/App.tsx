import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import AuthCallbackPage from './pages/AuthCallbackPage'
import HomePage from './pages/HomePage'
import DiscoverPage from './pages/DiscoverPage'
import MatchesPage from './pages/MatchesPage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import MyPacksPage from './pages/MyPacksPage'
import PackDetailPage from './pages/PackDetailPage'
import PackFormPage from './pages/PackFormPage'
import ProfileEditPage from './pages/ProfileEditPage'
import FursonaManagerPage from './pages/FursonaManagerPage'
import InboxPage from './pages/InboxPage'
import ConversationViewPage from './pages/ConversationViewPage'
import NotificationsPage from './pages/NotificationsPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/matches" element={<MatchesPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/inbox/:conversationId" element={<ConversationViewPage />} />
          <Route path="/packs" element={<DiscoverPage initialTab="packs" />} />
          <Route path="/my-packs" element={<MyPacksPage />} />
          <Route path="/packs/new" element={<PackFormPage />} />
          <Route path="/packs/:packId" element={<PackDetailPage />} />
          <Route path="/packs/:packId/edit" element={<PackFormPage />} />
          <Route path="/profile" element={<Navigate to="/profile/edit" replace />} />
          <Route path="/profile/edit" element={<ProfileEditPage />} />
          <Route path="/fursonas" element={<FursonaManagerPage />} />
        </Route>
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}

export default App
