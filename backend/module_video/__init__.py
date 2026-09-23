"""Story-style avatar videos for a course module.

Flow: the teacher has an agent draft a short story script from the module's
lessons, edits it, approves it, then renders it. Rendering goes through a
swappable `VideoRenderer` (renderers/); until a real video provider is
configured the default renderer produces a *storyboard* -- the approved
script played scene by scene with captions and optional browser narration --
so the whole flow works end to end without a paid provider.
"""
