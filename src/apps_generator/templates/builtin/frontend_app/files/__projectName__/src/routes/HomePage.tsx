export function HomePage() {
  return (
    <div{% if features.tailwind %} className="p-6"{% endif %}>
      <h1{% if features.tailwind %} className="text-2xl font-bold mb-4"{% endif %}>
        {{ projectTitle or projectName }}
      </h1>
      <p{% if features.tailwind %} className="text-gray-600"{% endif %}>
        Welcome to the {{ projectTitle or projectName }} micro-frontend.
      </p>
    </div>
  );
}
