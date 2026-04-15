import { describe, it, expect, vi, beforeEach } from "vitest";
import { createApiClient } from "../src/client";
import { ApiError } from "../src/types";

const mockConfig = {
  baseUrl: "http://localhost:8080",
  getToken: vi.fn().mockResolvedValue("test-token"),
  getTenantId: vi.fn().mockReturnValue("tenant-123"),
};

describe("createApiClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it("should add auth and tenant headers", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: "test" }),
    });

    const client = createApiClient(mockConfig);
    await client.get("/test");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8080/test",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
          "X-Tenant-ID": "tenant-123",
        }),
      }),
    );
  });

  it("should throw ApiError on 401", async () => {
    const onUnauthorized = vi.fn();
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve("Unauthorized"),
    });

    const client = createApiClient({ ...mockConfig, onUnauthorized });

    await expect(client.get("/test")).rejects.toThrow(ApiError);
    expect(onUnauthorized).toHaveBeenCalled();
  });

  it("should handle query params", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    const client = createApiClient(mockConfig);
    await client.get("/orders", { params: { page: "1", size: "10" } });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8080/orders?page=1&size=10",
      expect.anything(),
    );
  });
});
