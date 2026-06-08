/*
 * data-loader-example.js
 * ----------------------
 * Example of how a public page can load the question database exported by the
 * Django admin (`python manage.py export_questions` / `publish_questions`).
 *
 * The export lives at /data/questions.json relative to the site root, so it is
 * reachable at https://medicalpromax.ir/data/questions.json
 *
 * Each record has the shape:
 *   {
 *     id, subject, chapter, topic, source, book, exam_year, exam_name,
 *     question_number, difficulty, question_type, stem,
 *     options: [a, b, c, d], correct_option: 1|2|3|4,
 *     explanation, option_analysis, reference_text, teaching_note, tags, updated_at
 *   }
 *
 * This file is a standalone reference; it does not modify the existing site.
 */
(function () {
  "use strict";

  async function loadQuestions() {
    const res = await fetch("data/questions.json", { cache: "no-cache" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  loadQuestions()
    .then(function (questions) {
      console.log("Loaded " + questions.length + " questions");
      // Example: render the first question's stem and options.
      const q = questions[0];
      if (!q) return;
      const labels = ["الف", "ب", "ج", "د"];
      console.log("Stem:", q.stem);
      (q.options || []).forEach(function (opt, i) {
        console.log(labels[i] + ") " + opt);
      });
      console.log("Correct option:", q.correct_option);
    })
    .catch(function (err) {
      console.error("Failed to load questions.json:", err);
    });
})();
