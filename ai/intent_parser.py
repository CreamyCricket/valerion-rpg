from dataclasses import dataclass


@dataclass(frozen=True)
class IntentParseResult:
    """Simple structured output for safe natural-language inputs."""

    raw_text: str
    normalized_text: str
    intent: str
    target: str = ""
    topic: str = ""
    safe: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        result: dict[str, str | bool] = {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "intent": self.intent,
            "safe": self.safe,
        }
        if self.target:
            result["target"] = self.target
        if self.topic:
            result["topic"] = self.topic
        return result


class IntentParser:
    """Small v1 parser for safe and validated natural-language RPG intents."""

    READ_ONLY_INTENTS = {"observe", "inspect", "ask", "greet", "listen", "study"}
    ACTION_INTENTS = {"move", "fight", "take", "use"}
    AREA_TARGETS = {"", "area", "around", "around here", "surroundings", "room", "location", "here"}
    ASK_ABOUT_PREFIX = "about "
    OBSERVE_EXACT = {
        "look",
        "look around",
        "look about",
        "observe",
        "observe area",
        "observe surroundings",
        "scan area",
        "scan surroundings",
        "survey area",
        "survey surroundings",
    }
    OBSERVE_FOR_PREFIXES = ("watch for ", "scan for ", "survey for ")
    OBSERVE_PREFIXES = ("observe ", "watch ", "scan ", "survey ")
    INSPECT_PREFIXES = ("inspect ", "examine ", "look at ", "check ", "read ", "investigate ")
    ASK_PREFIXES = ("ask ", "question ", "talk to ", "speak to ", "speak with ")
    GREET_PREFIXES = ("greet ", "hello ", "hi ", "wave to ", "say hello to ", "say hi to ")
    GREET_FILLERS = {"all", "everybody", "everyone", "folks", "friend", "friends", "there"}
    LISTEN_PREFIXES = ("listen for ", "listen to ", "listen ", "hear ")
    MOVE_PREFIXES = ("go to ", "go ", "travel to ", "travel ", "head to ", "walk to ", "move to ", "enter ")
    FIGHT_PREFIXES = ("attack ", "fight ", "strike ", "hit ", "kill ")
    TAKE_PREFIXES = ("pick up ", "take ", "grab ", "loot ")
    USE_PREFIXES = ("drink ", "use ", "equip ", "wield ", "consume ", "quaff ")
    RESTRICTED_EXACT = {
        "buy",
        "leave",
        "load",
        "quit",
        "rest",
        "run",
        "save",
        "sell",
        "sleep",
    }
    RESTRICTED_PREFIXES = (
        "activate ",
        "break ",
        "buy ",
        "climb ",
        "eat ",
        "leave ",
        "load ",
        "open ",
        "pull ",
        "push ",
        "rest ",
        "run ",
        "save ",
        "sell ",
        "sleep ",
        "touch ",
        "wear ",
    )

    def parse(self, text: str) -> IntentParseResult:
        raw_text = " ".join(text.strip().split())
        normalized = self._normalize(text)
        if not normalized:
            return self._result(raw_text, normalized, "unknown")

        inspect_prefix = self._starts_with_any(normalized, self.INSPECT_PREFIXES)
        if inspect_prefix:
            return self._result(
                raw_text,
                normalized,
                "inspect",
                target=self._clean_fragment(normalized[len(inspect_prefix):]),
                safe=True,
            )
        if normalized == "inspect":
            return self._result(raw_text, normalized, "inspect", safe=True)

        if normalized.startswith("study "):
            return self._result(
                raw_text,
                normalized,
                "study",
                target=self._clean_fragment(normalized[len("study "):]),
                safe=True,
            )
        if normalized == "study":
            return self._result(raw_text, normalized, "study", safe=True)

        ask_prefix = self._starts_with_any(normalized, self.ASK_PREFIXES)
        if ask_prefix:
            return self._parse_ask(raw_text, normalized, normalized[len(ask_prefix):])
        if normalized in {"ask", "question"}:
            return self._result(raw_text, normalized, "ask", safe=True)

        greet_prefix = self._starts_with_any(normalized, self.GREET_PREFIXES)
        if greet_prefix:
            return self._result(
                raw_text,
                normalized,
                "greet",
                target=self._clean_fragment(normalized[len(greet_prefix):]),
                safe=True,
            )
        if normalized in {"greet", "hello", "hi"}:
            return self._result(raw_text, normalized, "greet", safe=True)

        listen_prefix = self._starts_with_any(normalized, self.LISTEN_PREFIXES)
        if listen_prefix:
            target = self._clean_fragment(normalized[len(listen_prefix):])
            if target in self.AREA_TARGETS:
                target = "area"
            return self._result(raw_text, normalized, "listen", target=target, safe=True)
        if normalized == "listen":
            return self._result(raw_text, normalized, "listen", target="area", safe=True)

        move_prefix = self._starts_with_any(normalized, self.MOVE_PREFIXES)
        if move_prefix:
            return self._result(
                raw_text,
                normalized,
                "move",
                target=self._clean_action_target(normalized[len(move_prefix):]),
            )
        if normalized in {"go", "travel", "move", "enter", "walk"}:
            return self._result(raw_text, normalized, "move")

        fight_prefix = self._starts_with_any(normalized, self.FIGHT_PREFIXES)
        if fight_prefix:
            return self._result(
                raw_text,
                normalized,
                "fight",
                target=self._clean_action_target(normalized[len(fight_prefix):]),
            )
        if normalized in {"attack", "fight", "strike", "hit", "kill"}:
            return self._result(raw_text, normalized, "fight")

        take_prefix = self._starts_with_any(normalized, self.TAKE_PREFIXES)
        if take_prefix:
            return self._result(
                raw_text,
                normalized,
                "take",
                target=self._clean_action_target(normalized[len(take_prefix):]),
            )
        if normalized in {"take", "grab", "loot", "pick"}:
            return self._result(raw_text, normalized, "take")

        use_prefix = self._starts_with_any(normalized, self.USE_PREFIXES)
        if use_prefix:
            return self._result(
                raw_text,
                normalized,
                "use",
                target=self._clean_action_target(normalized[len(use_prefix):]),
            )
        if normalized in {"drink", "use", "equip", "wield", "consume", "quaff"}:
            return self._result(raw_text, normalized, "use")

        if normalized in self.OBSERVE_EXACT:
            return self._result(raw_text, normalized, "observe", target="area", safe=True)

        observe_for_prefix = self._starts_with_any(normalized, self.OBSERVE_FOR_PREFIXES)
        if observe_for_prefix:
            target = self._clean_fragment(normalized[len(observe_for_prefix):]) or "area"
            return self._result(raw_text, normalized, "observe", target=target, safe=True)

        observe_prefix = self._starts_with_any(normalized, self.OBSERVE_PREFIXES)
        if observe_prefix:
            target = self._clean_fragment(normalized[len(observe_prefix):])
            if target in self.AREA_TARGETS:
                return self._result(raw_text, normalized, "observe", target="area", safe=True)
            return self._result(raw_text, normalized, "inspect", target=target, safe=True)

        if self._is_restricted(normalized):
            return self._result(raw_text, normalized, "restricted")

        return self._result(raw_text, normalized, "unknown")

    def _parse_ask(self, raw_text: str, normalized: str, payload: str) -> IntentParseResult:
        if payload.startswith(self.ASK_ABOUT_PREFIX):
            return self._result(
                raw_text,
                normalized,
                "ask",
                topic=self._clean_fragment(payload[len(self.ASK_ABOUT_PREFIX):]),
                safe=True,
            )

        if " about " in payload:
            target_text, topic_text = payload.split(" about ", maxsplit=1)
            return self._result(
                raw_text,
                normalized,
                "ask",
                target=self._clean_fragment(target_text),
                topic=self._clean_fragment(topic_text),
                safe=True,
            )

        return self._result(
            raw_text,
            normalized,
            "ask",
            target=self._clean_fragment(payload),
            safe=True,
        )

    def _is_restricted(self, normalized: str) -> bool:
        return normalized in self.RESTRICTED_EXACT or self._starts_with_any(normalized, self.RESTRICTED_PREFIXES) is not None

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().lower().split())

    @staticmethod
    def _starts_with_any(text: str, prefixes: tuple[str, ...]) -> str | None:
        for prefix in prefixes:
            if text.startswith(prefix):
                return prefix
        return None

    @classmethod
    def _clean_fragment(cls, text: str) -> str:
        cleaned = cls._normalize(text).strip(" .,!?:;\"'")
        cleaned = cls._strip_leading_article(cleaned)
        if cleaned in cls.GREET_FILLERS:
            return ""
        return cleaned

    @classmethod
    def _clean_action_target(cls, text: str) -> str:
        cleaned = cls._clean_fragment(text)
        for prefix in ("to ", "toward ", "towards ", "into ", "at "):
            if cleaned.startswith(prefix):
                return cls._strip_leading_article(cleaned[len(prefix):].strip())
        return cleaned

    @staticmethod
    def _strip_leading_article(text: str) -> str:
        for prefix in ("the ", "a ", "an "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return text

    @staticmethod
    def _result(
        raw_text: str,
        normalized_text: str,
        intent: str,
        target: str = "",
        topic: str = "",
        safe: bool = False,
    ) -> IntentParseResult:
        return IntentParseResult(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent=intent,
            target=target,
            topic=topic,
            safe=safe,
        )
