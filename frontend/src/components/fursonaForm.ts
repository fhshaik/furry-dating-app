export const TRAITS = [
  'adventurous',
  'calm',
  'creative',
  'energetic',
  'intellectual',
  'mischievous',
  'nurturing',
  'playful',
  'protective',
  'shy',
]

export interface Fursona {
  id: number
  name: string
  species: string
  traits: string[] | null
  description: string | null
  image_url: string | null
  is_primary: boolean
  is_nsfw: boolean
  created_at: string
}
