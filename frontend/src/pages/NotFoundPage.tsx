import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <h1 className="text-4xl font-bold text-gray-900">404</h1>
      <p className="mt-2 text-lg text-gray-600">Page not found.</p>
      <Link to="/" className="mt-6 text-indigo-600 hover:underline">
        Go home
      </Link>
    </div>
  )
}
