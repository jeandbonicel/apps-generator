export function AboutPage() {
  return (
    <div{% if features.tailwind %} className="p-6"{% endif %}>
      <h1{% if features.tailwind %} className="text-2xl font-bold mb-4"{% endif %}>
        About
      </h1>
      <p{% if features.tailwind %} className="text-gray-600"{% endif %}>
        This is a Module Federation remote micro-frontend built with React,
        Vite, and TypeScript.
      </p>
    </div>
  );
}
