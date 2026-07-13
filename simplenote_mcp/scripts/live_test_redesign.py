#!/usr/bin/env python3
"""Live end-to-end test of the Claude-companion redesign (Phases 8-10).

Spawns the *actual* simplenote-mcp-server subprocess and drives it over the
real MCP stdio JSON-RPC protocol with mcp.ClientSession — the same path
Claude Desktop uses — against the live Simplenote account. This exercises
the full stack (registry, security validation, cache, vault.py, real
Simplenote API calls, and the actual wire-level serialization) rather than
calling handler functions in-process.

Covers what unit tests (mocked Simplenote client) cannot prove:
  - Vault encryption round-trips through the real Simplenote API
  - Encrypted note bodies never leak into search results over the wire
  - MCP Resources' `_meta` field actually survives real JSON-RPC serialization
  - The session-handoff prompt is retrievable via the real protocol

All test notes are prefixed "LiveTest-Redesign-" and trashed at the end,
including on error (see the `finally` block).

Usage:
    SIMPLENOTE_WRITE_MODE=true .venv/bin/python simplenote_mcp/scripts/live_test_redesign.py
"""

import asyncio
import json
import os
import sys
import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PREFIX = "LiveTest-Redesign-"
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    results.append((name, condition, detail))
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    return condition


def tool_json(result) -> dict:
    return json.loads(result.content[0].text)


async def main() -> int:
    if not os.environ.get("SIMPLENOTE_EMAIL") or not os.environ.get(
        "SIMPLENOTE_PASSWORD"
    ):
        print("SIMPLENOTE_EMAIL / SIMPLENOTE_PASSWORD not set — aborting.")
        return 1

    env = dict(os.environ)
    env["SIMPLENOTE_WRITE_MODE"] = "true"
    env.setdefault("LOG_LEVEL", "WARNING")

    created_note_ids: list[str] = []

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "simplenote_mcp"],
        env=env,
    )

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session: ClientSession = await stack.enter_async_context(
            ClientSession(read, write)
        )
        await session.initialize()

        try:
            # -----------------------------------------------------------
            print("\n=== Tool registry ===")
            tools = (await session.list_tools()).tools
            tool_names = {t.name for t in tools}
            check("30 tools registered", len(tools) == 30, f"got {len(tools)}")
            for expected in ("encrypt_note", "decrypt_note", "vault_status"):
                check(f"{expected} registered", expected in tool_names)

            # -----------------------------------------------------------
            print("\n=== vault_status (before) ===")
            status_before = tool_json(await session.call_tool("vault_status", {}))
            print(
                f"  key_available={status_before.get('key_available')} "
                f"provider={status_before.get('key_provider')} "
                f"encrypted_count={status_before.get('encrypted_note_count')}"
            )
            check("vault_status succeeds", status_before.get("success") is True)
            key_available = bool(status_before.get("key_available"))
            if not key_available:
                print(
                    "  (no Vault key provisioned yet — create_note with encrypt=true "
                    "will provision one via the OS keychain, may prompt once)"
                )

            # -----------------------------------------------------------
            print("\n=== Vault: create_note(encrypt=true) ===")
            secret_marker = f"live-test-secret-{int(time.time())}"
            title = f"{PREFIX}Vault {int(time.time())}"
            create_result = tool_json(
                await session.call_tool(
                    "create_note",
                    {
                        "content": f"{title}\nvery sensitive body containing {secret_marker}",
                        "tags": ["live-test"],
                        "encrypt": True,
                    },
                )
            )
            note_id = create_result.get("note_id")
            if note_id:
                created_note_ids.append(note_id)
            check(
                "create_note(encrypt=true) succeeds",
                create_result.get("success") is True,
            )
            check(
                "response reports encrypted=true",
                create_result.get("encrypted") is True,
            )
            check(
                "vault-encrypted tag present",
                "vault-encrypted" in (create_result.get("tags") or []),
            )

            # -----------------------------------------------------------
            print("\n=== Vault: get_note decrypts transparently ===")
            await asyncio.sleep(1)  # let Simplenote settle
            got = tool_json(await session.call_tool("get_note", {"note_id": note_id}))
            check("get_note succeeds", got.get("success") is True)
            check("encrypted=true", got.get("encrypted") is True)
            check("decryptable=true", got.get("decryptable") is True)
            check(
                "decrypted content matches original",
                secret_marker in (got.get("content") or ""),
            )
            # title is truncated to config.title_max_length (default 30 chars)
            # by tool_handlers.extract_title_from_content — a prefix match is
            # the correct check, not exact equality.
            check(
                "title still readable",
                bool(got.get("title")) and title.startswith(got.get("title") or "\0"),
            )

            # -----------------------------------------------------------
            print("\n=== Vault: encrypted body never leaks into search ===")
            search_secret = tool_json(
                await session.call_tool(
                    "search_notes",
                    {"query": secret_marker.split("-")[-1] and secret_marker},
                )
            )
            leaked = any(
                secret_marker in json.dumps(r) for r in search_secret.get("results", [])
            )
            check("search for secret body text finds nothing", not leaked)

            search_title = tool_json(
                await session.call_tool("search_notes", {"query": title})
            )
            found_by_title = any(
                r.get("id") == note_id for r in search_title.get("results", [])
            )
            check("search for plaintext title still finds the note", found_by_title)
            if found_by_title:
                matched = next(r for r in search_title["results"] if r["id"] == note_id)
                check(
                    "search result marks it encrypted, snippet has no ciphertext",
                    matched.get("encrypted") is True
                    and "SNVAULT" not in matched.get("snippet", ""),
                )

            # -----------------------------------------------------------
            print("\n=== Vault: decrypt_note reverses it ===")
            decrypted = tool_json(
                await session.call_tool("decrypt_note", {"note_id": note_id})
            )
            check("decrypt_note succeeds", decrypted.get("success") is True)
            check("encrypted=false after decrypt", decrypted.get("encrypted") is False)

            after_decrypt = tool_json(
                await session.call_tool("get_note", {"note_id": note_id})
            )
            check(
                "content readable without decryption after decrypt_note",
                secret_marker in (after_decrypt.get("content") or ""),
            )
            check(
                "encrypted=false on get_note too",
                after_decrypt.get("encrypted") is False,
            )

            # -----------------------------------------------------------
            print(
                "\n=== Vault: encrypt_note re-encrypts an existing plaintext note ==="
            )
            reencrypted = tool_json(
                await session.call_tool("encrypt_note", {"note_id": note_id})
            )
            check("encrypt_note succeeds", reencrypted.get("success") is True)
            check("encrypted=true again", reencrypted.get("encrypted") is True)

            # -----------------------------------------------------------
            print("\n=== Vault: add_text refuses on an encrypted note ===")
            guarded = await session.call_tool(
                "add_text", {"note_id": note_id, "text": "should be refused"}
            )
            guarded_data = tool_json(guarded)
            check(
                "add_text refuses with vault_encrypted_note",
                guarded_data.get("success") is False
                and guarded_data.get("error", {}).get("subcategory")
                == "vault_encrypted_note",
            )

            # -----------------------------------------------------------
            print("\n=== vault_status (after) ===")
            status_after = tool_json(await session.call_tool("vault_status", {}))
            check(
                "encrypted_note_count increased by at least 1",
                status_after.get("encrypted_note_count", 0)
                >= status_before.get("encrypted_note_count", 0) + 1,
            )

            # -----------------------------------------------------------
            print("\n=== MCP Resources: _meta carries tags/dates/pagination ===")
            plain_title = f"{PREFIX}Resource {int(time.time())}"
            plain_note = tool_json(
                await session.call_tool(
                    "create_note",
                    {
                        "content": f"{plain_title}\nplain body for resource test",
                        "tags": ["live-test", "resource-check"],
                    },
                )
            )
            plain_id = plain_note.get("note_id")
            if plain_id:
                created_note_ids.append(plain_id)
            await asyncio.sleep(1)

            resources = await session.list_resources()
            check(
                "list_resources returns at least one resource",
                len(resources.resources) > 0,
            )
            our_resource = next(
                (
                    r
                    for r in resources.resources
                    if str(r.uri) == f"simplenote://note/{plain_id}"
                ),
                None,
            )
            check("our note appears in list_resources", our_resource is not None)
            if our_resource is not None:
                meta = our_resource.meta or {}
                check(
                    "resource._meta carries real tags array",
                    "resource-check" in (meta.get("tags") or []),
                )
                check(
                    "resource description mentions tags",
                    "resource-check" in (our_resource.description or ""),
                )

            first = resources.resources[0] if resources.resources else None
            check(
                "first resource carries pagination in _meta",
                bool(first and (first.meta or {}).get("pagination")),
            )

            read_result = await session.read_resource(f"simplenote://note/{plain_id}")
            content0 = read_result.contents[0]
            check(
                "read_resource content._meta carries tags",
                "resource-check" in ((content0.meta or {}).get("tags") or []),
            )

            # -----------------------------------------------------------
            print("\n=== MCP Prompts: session_handoff_prompt ===")
            prompts = (await session.list_prompts()).prompts
            prompt_names = {p.name for p in prompts}
            check("3 prompts registered", len(prompts) == 3, f"got {len(prompts)}")
            check(
                "session_handoff_prompt registered",
                "session_handoff_prompt" in prompt_names,
            )

            handoff = await session.get_prompt(
                "session_handoff_prompt",
                {
                    "project": "live-test-project",
                    "status": "verifying redesign end-to-end",
                    "next_steps": "none — this is the verification run",
                    "blockers": "none",
                },
            )
            combined = " ".join(
                m.content.text for m in handoff.messages if hasattr(m.content, "text")
            )
            check(
                "prompt references get_or_create_note", "get_or_create_note" in combined
            )
            check("prompt references add_text", "add_text" in combined)
            check("prompt includes project name", "live-test-project" in combined)

        finally:
            print("\n=== Cleanup: trashing test notes ===")
            for nid in created_note_ids:
                try:
                    del_result = tool_json(
                        await session.call_tool("delete_note", {"note_id": nid})
                    )
                    ok = del_result.get("success") is True
                    print(f"  [{'ok' if ok else 'FAILED'}] trashed {nid}")
                except Exception as e:  # noqa: BLE001
                    print(f"  [FAILED] trashing {nid}: {e}")

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"RESULTS: {passed}/{total} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name}" + (f" ({detail})" if detail else ""))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
