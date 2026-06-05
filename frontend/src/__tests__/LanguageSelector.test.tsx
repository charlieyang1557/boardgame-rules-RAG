import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { LanguageSelector } from "../components/LanguageSelector";

describe("LanguageSelector", () => {
  it("renders EN and 中文 options", () => {
    render(<LanguageSelector selectedLanguage="en" onLanguageChange={() => {}} />);
    const select = screen.getByLabelText("Language") as HTMLSelectElement;
    expect(select.value).toBe("en");
    expect(screen.getByRole("option", { name: "EN" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "中文" })).toBeInTheDocument();
  });

  it("fires onLanguageChange when a language is selected", async () => {
    const onChange = vi.fn();
    render(<LanguageSelector selectedLanguage="en" onLanguageChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText("Language"), "zh");
    expect(onChange).toHaveBeenCalledWith("zh");
  });
});
