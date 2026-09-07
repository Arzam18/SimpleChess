#pragma once

// -----------------------------------------------------------------------------
// syzygy.hpp
//
// Endgame-tablebase probing via the vendored Fathom library (external/Fathom).
// A thin bridge: it converts the engine's Board into Fathom's bitboard inputs,
// gates probing to positions Fathom can answer (few enough men, no castling
// rights, halfmove clock at zero — Fathom's WDL helper requires the last two),
// and maps the win/draw/loss verdict into the engine's VALUE_TB_* score band.
//
// Compiled in by default. It is entirely INERT until a SyzygyPath is loaded:
// with no tables, max_men() and probe_limit() return 0, so every search-side
// gate is false and the engine behaves byte-for-byte as if this code were
// absent. Build with -DSC_SYZYGY=0 to compile the probing out (control builds).
// -----------------------------------------------------------------------------

#include <optional>
#include <string>

#include "types.hpp"

#ifndef SC_SYZYGY
#define SC_SYZYGY 1
#endif

namespace engine::syzygy {

// Load tablebases from `path` (Fathom multi-directory syntax). Releases any
// prior load first. Returns the max number of men in the loaded tables (0 = none
// found / disabled / empty path).
int init(const std::string& path);

// Release the loaded tables (call on re-init and on quit).
void teardown();

// Max men in the loaded tables (0 = none). Cheap; safe on the probe hot path.
[[nodiscard]] int max_men();

// Effective piece cap for probing = min(the SyzygyProbeLimit option, max_men());
// 0 when no tables are loaded, which disables every caller's gate.
[[nodiscard]] int probe_limit();

// Minimum remaining search depth at which interior nodes are probed.
[[nodiscard]] int probe_depth();

void set_probe_depth(int d);
void set_probe_limit(int men);
void set_fifty_rule(bool on);   // respect the 50-move rule (cursed/blessed -> draw)

// Per-search tablebase-hit counter (for `info ... tbhits`).
[[nodiscard]] std::uint64_t hits();
void reset_hits();

// WDL probe of a search node at `ply`. Returns a VALUE_TB_* score (ply-encoded so
// a nearer TB win outranks a farther one) on a clean hit, or nullopt when the
// position is not probeable (castling rights present, halfmove clock != 0, more
// than max_men() pieces, or a Fathom miss). Increments the hit counter on a hit.
// Thread-safe (Fathom's WDL probe is; the config globals are atomics).
[[nodiscard]] std::optional<Value> probe_wdl(const Board& board, int ply);

}  // namespace engine::syzygy
