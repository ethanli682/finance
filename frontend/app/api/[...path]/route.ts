// Forwards browser requests to the Python API so the frontend and backend share
// an origin (no CORS) and the backend URL stays a runtime setting.
import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  const target = new URL(`/api/${path.map(encodeURIComponent).join("/")}`, API_URL);
  target.search = request.nextUrl.search;

  try {
    const upstream = await fetch(target, { cache: "no-store", headers: { accept: "application/json" } });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { detail: "The data service isn't reachable. Check that the backend is running." },
      { status: 502 },
    );
  }
}
