from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents import create_agent
from agents.intentional_agent import IntentionalAgent
from hanabi.analysis import (
    DISCARD,
    KEEP,
    MAY_DISCARD,
    PLAY,
    best_hint_assessment,
    discard_assessments,
    form_intentions,
    legal_hint_assessments,
)
from hanabi.cards import COLORS, Card
from hanabi.deck import shuffled_deck
from hanabi.game import HanabiGame
from hanabi.rules import card_is_known_playable, card_is_known_useless
from hanabi.state import Action, GameEvent, TurnView

CARD_COLORS: dict[str, tuple[str, str]] = {
    "green": ("#2a9d8f", "#ffffff"),
    "yellow": ("#e9c46a", "#2b2118"),
    "white": ("#f4f1de", "#1f1f1f"),
    "blue": ("#457b9d", "#ffffff"),
    "red": ("#b23a48", "#ffffff"),
}
INTENTION_LABELS = {
    PLAY: "Play",
    DISCARD: "Discard",
    MAY_DISCARD: "May Discard",
    KEEP: "Keep",
}


def summarize_possibilities(card, limit: int = 8) -> str:
    possibilities = sorted(
        card.possible_cards_with_counts(),
        key=lambda item: (item[0].rank, COLORS.index(item[0].color)),
    )
    if not possibilities:
        return "No legal identities"
    parts = [f"{identity.short}x{count}" for identity, count in possibilities[:limit]]
    if len(possibilities) > limit:
        parts.append("...")
    return ", ".join(parts)


def describe_hint(action: Action) -> str:
    assert action.hint is not None
    if action.hint.kind == "color":
        return f"Color {action.hint.value}"
    return f"Rank {action.hint.value}"


def describe_action(action: Action) -> str:
    if action.kind == "play":
        return f"Play slot {action.card_index + 1}"
    if action.kind == "discard":
        return f"Discard slot {action.card_index + 1}"
    return f"Hint {describe_hint(action)}"


def format_event(event: GameEvent) -> str:
    actor = "You" if event.actor == 0 else "AI"
    if event.action.kind == "hint":
        assert event.action.hint is not None
        targets = ", ".join(str(index + 1) for index in event.positive_indices) or "none"
        return f"{actor} gave {describe_hint(event.action)} to slots [{targets}]."
    if event.revealed_card is None:
        return f"{actor} acted."
    if event.action.kind == "play":
        outcome = "success" if event.success else "fail"
        return f"{actor} played {event.revealed_card} ({outcome})."
    return f"{actor} discarded {event.revealed_card}."


class HanabiTkApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Intentional Hanabi")
        self.geometry("1480x980")
        self.configure(bg="#f6efe4")

        self.game: HanabiGame | None = None
        self.ai_agent = None
        self.intentional_probe = IntentionalAgent()
        self.ai_turn_scheduled = False

        self.opponent_var = tk.StringVar(value="full")
        self.seed_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="Choose an opponent and start a game.")

        self._build_shell()
        self.new_game()

    def _build_shell(self) -> None:
        header = tk.Frame(self, bg="#18323f", padx=18, pady=14)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Intentional Hanabi",
            bg="#18323f",
            fg="#f7f2e9",
            font=("Georgia", 24, "bold"),
        ).pack(side="left")

        controls = tk.Frame(header, bg="#18323f")
        controls.pack(side="right")

        tk.Label(controls, text="Opponent", bg="#18323f", fg="#f7f2e9", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, padx=(0, 8))
        opponent_box = ttk.Combobox(
            controls,
            textvariable=self.opponent_var,
            values=("outer", "intentional", "full"),
            width=14,
            state="readonly",
        )
        opponent_box.grid(row=0, column=1, padx=(0, 12))

        tk.Label(controls, text="Seed", bg="#18323f", fg="#f7f2e9", font=("Segoe UI", 11, "bold")).grid(row=0, column=2, padx=(0, 8))
        tk.Entry(
            controls,
            textvariable=self.seed_var,
            width=10,
            bg="#f7f2e9",
            fg="#1d1b19",
            relief="flat",
            font=("Consolas", 11),
        ).grid(row=0, column=3, padx=(0, 12))

        tk.Button(
            controls,
            text="New Game",
            command=self.new_game,
            bg="#d9a441",
            fg="#1d1b19",
            activebackground="#e1b45d",
            relief="flat",
            padx=14,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=4)

        status_bar = tk.Frame(self, bg="#f6efe4", padx=18, pady=8)
        status_bar.pack(fill="x")
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg="#f6efe4",
            fg="#2b2b2b",
            font=("Segoe UI", 11),
        ).pack(anchor="w")

        self.main_frame = tk.Frame(self, bg="#f6efe4", padx=18, pady=10)
        self.main_frame.pack(fill="both", expand=True)

        self.board_frame = tk.Frame(self.main_frame, bg="#f6efe4")
        self.board_frame.pack(fill="both", expand=True)

        self.left_panel = tk.Frame(self.board_frame, bg="#f6efe4")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.center_panel = tk.Frame(self.board_frame, bg="#f6efe4")
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=12)

        self.right_panel = tk.Frame(self.board_frame, bg="#f6efe4")
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(12, 0))

        self.board_frame.grid_columnconfigure(0, weight=4)
        self.board_frame.grid_columnconfigure(1, weight=3)
        self.board_frame.grid_columnconfigure(2, weight=4)
        self.board_frame.grid_rowconfigure(0, weight=1)

        self.ai_hand_frame = tk.Frame(self.left_panel, bg="#f6efe4")
        self.ai_hand_frame.pack(fill="x", pady=(0, 14))

        self.human_hand_frame = tk.Frame(self.left_panel, bg="#f6efe4")
        self.human_hand_frame.pack(fill="both", expand=True)

        self.stats_frame = tk.Frame(self.center_panel, bg="#efe2cb", padx=14, pady=14, highlightbackground="#d5c3a1", highlightthickness=1)
        self.stats_frame.pack(fill="x")

        self.hint_frame = tk.Frame(self.center_panel, bg="#f6efe4")
        self.hint_frame.pack(fill="x", pady=14)

        self.log_frame = tk.Frame(self.center_panel, bg="#f6efe4")
        self.log_frame.pack(fill="both", expand=True)

        tk.Label(
            self.log_frame,
            text="Turn Log",
            bg="#f6efe4",
            fg="#1d1b19",
            font=("Georgia", 16, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self.log_text = ScrolledText(
            self.log_frame,
            height=18,
            wrap="word",
            bg="#fffaf1",
            fg="#1d1b19",
            relief="flat",
            font=("Consolas", 10),
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        tk.Label(
            self.right_panel,
            text="Paper Heuristic Inspector",
            bg="#f6efe4",
            fg="#1d1b19",
            font=("Georgia", 16, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self.heuristic_text = ScrolledText(
            self.right_panel,
            wrap="word",
            bg="#fffaf1",
            fg="#1d1b19",
            relief="flat",
            font=("Consolas", 10),
        )
        self.heuristic_text.pack(fill="both", expand=True)
        self.heuristic_text.configure(state="disabled")

    def new_game(self) -> None:
        try:
            seed_text = self.seed_var.get().strip()
            deck = shuffled_deck(int(seed_text)) if seed_text else None
        except ValueError:
            messagebox.showerror("Bad Seed", "Seed must be an integer or blank for a random shuffle.")
            return

        self.game = HanabiGame(deck=deck)
        self.ai_agent = create_agent(self.opponent_var.get())
        self.ai_agent.reset(1)
        self.ai_turn_scheduled = False
        self._set_log("")
        self.status_var.set(
            f"New game vs {self.opponent_var.get().title()}. You are Player 0 and act first."
        )
        self.render()

    def render(self) -> None:
        if self.game is None:
            return

        human_view = self.game.get_view_for(0)
        self._render_stats(human_view)
        self._render_ai_hand(human_view)
        self._render_human_hand(human_view)
        self._render_hint_controls(human_view)
        self._render_heuristic_panel(human_view)

        if self.game.is_done():
            self.status_var.set(
                f"Game over. Final score {self.game.score()} with {self.game.mistakes_made} mistakes."
            )
        elif self.game.current_player == 0:
            self.status_var.set("Your turn. Play, discard, or give a hint.")
        else:
            self.status_var.set(f"{self.opponent_var.get().title()} is thinking...")

        if self.game.current_player == 1 and not self.game.is_done() and not self.ai_turn_scheduled:
            self.ai_turn_scheduled = True
            self.after(450, self._run_ai_turn)

    def _render_stats(self, human_view: TurnView) -> None:
        for child in self.stats_frame.winfo_children():
            child.destroy()

        rows = [
            ("Score", str(self.game.score() if self.game is not None else 0)),
            ("Hints", f"{human_view.hints}/{human_view.max_hints}"),
            ("Mistakes", f"{human_view.mistakes_made}/{human_view.max_mistakes}"),
            ("Deck", str(human_view.deck_size)),
            ("Fireworks", ", ".join(f"{color[0].upper()}:{rank}" for color, rank in human_view.fireworks.items())),
            ("Discard", self._summarize_discard_pile(human_view.discard_pile)),
        ]
        for row, (label, value) in enumerate(rows):
            tk.Label(
                self.stats_frame,
                text=label,
                bg="#efe2cb",
                fg="#18323f",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(
                self.stats_frame,
                text=value,
                bg="#efe2cb",
                fg="#1d1b19",
                font=("Consolas", 10),
                anchor="w",
                justify="left",
            ).grid(row=row, column=1, sticky="w", pady=2, padx=(16, 0))

    def _render_ai_hand(self, human_view: TurnView) -> None:
        for child in self.ai_hand_frame.winfo_children():
            child.destroy()

        tk.Label(
            self.ai_hand_frame,
            text=f"AI Hand ({self.opponent_var.get().title()})",
            bg="#f6efe4",
            fg="#1d1b19",
            font=("Georgia", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        cards_row = tk.Frame(self.ai_hand_frame, bg="#f6efe4")
        cards_row.pack(fill="x")
        intentions = form_intentions(human_view.partner_hand, human_view.fireworks, human_view.discard_pile)
        for index, (card, intention) in enumerate(zip(human_view.partner_hand, intentions, strict=True)):
            card_bg, text_fg = CARD_COLORS[card.color]
            frame = tk.Frame(cards_row, bg=card_bg, bd=0, relief="flat", padx=10, pady=10)
            frame.pack(side="left", padx=(0, 10), ipadx=8, ipady=8)
            tk.Label(frame, text=f"Slot {index + 1}", bg=card_bg, fg=text_fg, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(frame, text=card.short, bg=card_bg, fg=text_fg, font=("Georgia", 20, "bold")).pack(anchor="w")
            tk.Label(frame, text=INTENTION_LABELS[intention], bg=card_bg, fg=text_fg, font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 0))

    def _render_human_hand(self, human_view: TurnView) -> None:
        for child in self.human_hand_frame.winfo_children():
            child.destroy()

        tk.Label(
            self.human_hand_frame,
            text="Your Hidden Hand",
            bg="#f6efe4",
            fg="#1d1b19",
            font=("Georgia", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        row = tk.Frame(self.human_hand_frame, bg="#f6efe4")
        row.pack(fill="both", expand=True)

        discard_scores = {assessment.card_index: assessment.score for assessment in discard_assessments(human_view)}
        human_turn = self.game is not None and self.game.current_player == 0 and not self.game.is_done()
        actual_cards = tuple(self.game.hands[0]) if self.game is not None else tuple()

        for index, mental_card in enumerate(human_view.my_mental_state.cards):
            frame = tk.Frame(
                row,
                bg="#22313f",
                padx=12,
                pady=12,
                highlightbackground="#3a5060",
                highlightthickness=1,
            )
            frame.pack(side="left", padx=(0, 10), fill="both", expand=True)

            tk.Label(frame, text=f"Slot {index + 1}", bg="#22313f", fg="#f6efe4", font=("Segoe UI", 11, "bold")).pack(anchor="w")

            possible = mental_card.possible_cards()
            if mental_card.is_identified():
                headline = f"Identified: {possible[0].short}"
            else:
                headline = f"{len(possible)} possible identities"
            tk.Label(frame, text=headline, bg="#22313f", fg="#f2c14e", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 0))

            facts = [
                f"Known playable: {'yes' if card_is_known_playable(mental_card, human_view.fireworks) else 'no'}",
                f"Known useless: {'yes' if card_is_known_useless(mental_card, human_view.fireworks, human_view.discard_pile) else 'no'}",
                f"Discard score: {discard_scores[index]:.2f}",
                f"Possibilities: {summarize_possibilities(mental_card)}",
            ]
            for fact in facts:
                tk.Label(
                    frame,
                    text=fact,
                    bg="#22313f",
                    fg="#f6efe4",
                    wraplength=220,
                    justify="left",
                    anchor="w",
                    font=("Consolas", 9),
                ).pack(anchor="w", pady=(6, 0))

            controls = tk.Frame(frame, bg="#22313f")
            controls.pack(anchor="w", pady=(12, 0))
            tk.Button(
                controls,
                text="Play",
                command=lambda card_index=index: self._handle_human_action(Action.play(card_index)),
                state="normal" if human_turn else "disabled",
                bg="#2a9d8f",
                fg="#ffffff",
                relief="flat",
                padx=12,
                pady=4,
            ).pack(side="left", padx=(0, 6))
            tk.Button(
                controls,
                text="Discard",
                command=lambda card_index=index: self._handle_human_action(Action.discard(card_index)),
                state="normal" if human_turn else "disabled",
                bg="#b56576",
                fg="#ffffff",
                relief="flat",
                padx=12,
                pady=4,
            ).pack(side="left")

            if self.game is not None and self.game.is_done():
                tk.Label(
                    frame,
                    text=f"Actual card: {actual_cards[index].short}",
                    bg="#22313f",
                    fg="#f2c14e",
                    font=("Segoe UI", 10, "bold"),
                ).pack(anchor="w", pady=(10, 0))

    def _render_hint_controls(self, human_view: TurnView) -> None:
        for child in self.hint_frame.winfo_children():
            child.destroy()

        tk.Label(
            self.hint_frame,
            text="Hint Controls",
            bg="#f6efe4",
            fg="#1d1b19",
            font=("Georgia", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        enabled = self.game is not None and self.game.current_player == 0 and not self.game.is_done() and human_view.hints > 0
        colors = sorted({card.color for card in human_view.partner_hand}, key=COLORS.index)
        ranks = sorted({card.rank for card in human_view.partner_hand})

        color_row = tk.Frame(self.hint_frame, bg="#f6efe4")
        color_row.pack(anchor="w", pady=(0, 6))
        tk.Label(color_row, text="Color hints:", bg="#f6efe4", fg="#1d1b19", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        for color in colors:
            bg, fg = CARD_COLORS[color]
            tk.Button(
                color_row,
                text=color.title(),
                command=lambda hinted=color: self._handle_human_action(Action.hint_color(1, hinted)),
                state="normal" if enabled else "disabled",
                bg=bg,
                fg=fg,
                relief="flat",
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 6))

        rank_row = tk.Frame(self.hint_frame, bg="#f6efe4")
        rank_row.pack(anchor="w")
        tk.Label(rank_row, text="Rank hints:", bg="#f6efe4", fg="#1d1b19", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        for rank in ranks:
            tk.Button(
                rank_row,
                text=str(rank),
                command=lambda hinted=rank: self._handle_human_action(Action.hint_rank(1, hinted)),
                state="normal" if enabled else "disabled",
                bg="#d9a441",
                fg="#1d1b19",
                relief="flat",
                padx=12,
                pady=4,
            ).pack(side="left", padx=(0, 6))

    def _render_heuristic_panel(self, human_view: TurnView) -> None:
        recommendation = self.intentional_probe.choose_action(human_view)
        intentions = form_intentions(human_view.partner_hand, human_view.fireworks, human_view.discard_pile)
        best_hint = best_hint_assessment(human_view)
        hint_assessments = legal_hint_assessments(human_view)
        discard_scores = discard_assessments(human_view)

        lines = [
            "Intentional recommendation",
            f"  {describe_action(recommendation)}",
            "",
            "Partner intentions",
        ]
        for index, intention in enumerate(intentions, start=1):
            lines.append(f"  Slot {index}: {INTENTION_LABELS[intention]}")

        lines.extend(["", "Discard heuristic"])
        for assessment in discard_scores:
            lines.append(f"  Slot {assessment.card_index + 1}: {assessment.score:.2f}")

        lines.extend(["", "Hint scoring"])
        if best_hint is None:
            lines.append("  No positive intentional hint available.")
        else:
            lines.append(f"  Best hint: {describe_hint(best_hint.action)} (score {best_hint.score})")

        for assessment in hint_assessments:
            label = describe_hint(assessment.action)
            if not assessment.valid:
                lines.append(f"  {label}: blocked")
            else:
                lines.append(f"  {label}: score {assessment.score}")

        if human_view.pending_received_hint is not None:
            lines.extend(
                [
                    "",
                    "Received hint",
                    f"  {human_view.pending_received_hint.hint}",
                    f"  Positive slots: {', '.join(str(i + 1) for i in human_view.pending_received_hint.positive_indices)}",
                ],
            )

        self._set_text_widget(self.heuristic_text, "\n".join(lines))

    def _handle_human_action(self, action: Action) -> None:
        if self.game is None or self.ai_agent is None or self.game.is_done() or self.game.current_player != 0:
            return

        try:
            event = self.game.apply_action(action)
        except ValueError as exc:
            messagebox.showerror("Illegal Action", str(exc))
            return

        self.ai_agent.observe(event)
        self._append_log(format_event(event))
        self.ai_turn_scheduled = False
        self.render()
        if self.game.is_done():
            self._announce_game_end()

    def _run_ai_turn(self) -> None:
        self.ai_turn_scheduled = False
        if self.game is None or self.ai_agent is None or self.game.is_done() or self.game.current_player != 1:
            return

        ai_view = self.game.get_view_for(1)
        action = self.ai_agent.choose_action(ai_view)
        event = self.game.apply_action(action)
        self.ai_agent.observe(event)
        self._append_log(format_event(event))
        self.render()
        if self.game.is_done():
            self._announce_game_end()

    def _announce_game_end(self) -> None:
        if self.game is None:
            return
        messagebox.showinfo(
            "Game Over",
            f"Final score: {self.game.score()}\nHints left: {self.game.hints}\nMistakes: {self.game.mistakes_made}",
        )

    def _summarize_discard_pile(self, discard_pile: tuple[Card, ...]) -> str:
        if not discard_pile:
            return "empty"
        counts: dict[str, int] = {}
        for card in discard_pile:
            counts[card.short] = counts.get(card.short, 0) + 1
        return ", ".join(f"{label}x{count}" for label, count in sorted(counts.items()))

    def _append_log(self, line: str) -> None:
        existing = self.log_text.get("1.0", "end").strip()
        content = f"{existing}\n{line}".strip()
        self._set_text_widget(self.log_text, content)
        self.log_text.see("end")

    def _set_log(self, content: str) -> None:
        self._set_text_widget(self.log_text, content)

    def _set_text_widget(self, widget: ScrolledText, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")


def main() -> None:
    app = HanabiTkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
