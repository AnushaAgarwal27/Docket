import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Join the waitlist. Signing up twice with the same email updates the row instead of adding another.
export const join = mutation({
  args: {
    name: v.string(),
    email: v.string(),
    school: v.optional(v.string()),
    visa: v.optional(v.union(v.literal("F-1"), v.literal("J-1"), v.literal("Neither"))),
  },
  handler: async (ctx, args) => {
    const name = args.name.trim().slice(0, 100);
    const email = args.email.trim().toLowerCase().slice(0, 200);
    if (!name) throw new Error("Please enter your name.");
    if (!EMAIL.test(email)) throw new Error("Please enter a valid email address.");
    const school = args.school?.trim().slice(0, 120) || undefined;
    const existing = await ctx.db.query("waitlist").withIndex("by_email", (q) => q.eq("email", email)).unique();
    if (existing) {
      await ctx.db.patch("waitlist", existing._id, { name, school, visa: args.visa });
      return { alreadyJoined: true };
    }
    await ctx.db.insert("waitlist", { name, email, school, visa: args.visa, createdAt: new Date().toISOString() });
    return { alreadyJoined: false };
  },
});

// How many people have joined, for the page (never returns names or emails).
export const count = query({
  args: {},
  handler: async (ctx) => {
    // Bounded read; a hackathon waitlist stays far below this.
    return (await ctx.db.query("waitlist").take(5000)).length;
  },
});
