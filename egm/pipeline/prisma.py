"""PRISMA flow with reconciliation assertions.

The superseded pipeline recorded 616 identified, 0 excluded, 616 included
across every stage (see DEPRECATED.md). validate() makes that unrepresentable.
"""
import csv
import pathlib

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.integrity import IntegrityError


class PrismaStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    identified: int = Field(ge=0)
    excluded: int = Field(ge=0)
    reason: str

    @model_validator(mode="after")
    def _check(self) -> "PrismaStage":
        if self.excluded > self.identified:
            raise ValueError(
                f"{self.name}: excluded ({self.excluded}) exceeds identified ({self.identified})"
            )
        if self.excluded > 0 and not self.reason.strip():
            raise ValueError(f"{self.name}: a non-zero exclusion requires a reason")
        return self

    @property
    def included(self) -> int:
        return self.identified - self.excluded


class PrismaFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: list[PrismaStage]

    def included_after(self, name: str) -> int:
        for stage in self.stages:
            if stage.name == name:
                return stage.included
        raise KeyError(f"no stage named {name!r}")

    def validate(self) -> None:
        """Raise IntegrityError if the flow is internally inconsistent."""
        if not self.stages:
            raise IntegrityError("PRISMA flow has no stages")

        for earlier, later in zip(self.stages, self.stages[1:]):
            if later.identified != earlier.included:
                raise IntegrityError(
                    f"carry-forward mismatch: {earlier.name} included {earlier.included} "
                    f"but {later.name} identified {later.identified}"
                )

        if sum(stage.excluded for stage in self.stages) == 0:
            raise IntegrityError(
                "zero exclusions across the entire flow: no screening occurred"
            )

    def to_csv(self, path: pathlib.Path) -> None:
        self.validate()
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stage", "identified", "excluded", "included", "reason"])
            for stage in self.stages:
                writer.writerow(
                    [stage.name, stage.identified, stage.excluded, stage.included, stage.reason]
                )
