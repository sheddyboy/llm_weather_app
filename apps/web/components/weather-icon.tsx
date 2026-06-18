import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  Cloudy,
  Moon,
  Sun,
  type LucideProps,
} from "lucide-react"
import { conditionGroup, isNight } from "@/lib/weather"

interface WeatherIconProps extends LucideProps {
  conditions: string | null | undefined
  /** Force a day/night variant; defaults to current local time. */
  night?: boolean
}

export function WeatherIcon({ conditions, night, ...props }: WeatherIconProps) {
  const group = conditionGroup(conditions)
  const dark = night ?? isNight()
  const c = (conditions || "").toLowerCase()

  switch (group) {
    case "thunderstorm":
      return <CloudLightning {...props} />
    case "snow":
      return <CloudSnow {...props} />
    case "rain":
      return c.includes("drizzle") ? <CloudDrizzle {...props} /> : <CloudRain {...props} />
    case "clouds":
      return c.includes("few") || c.includes("scattered") ? <Cloud {...props} /> : <Cloudy {...props} />
    case "mist":
      return <CloudFog {...props} />
    case "clear":
    default:
      return dark ? <Moon {...props} /> : <Sun {...props} />
  }
}
