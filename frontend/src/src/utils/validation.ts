import { z } from 'zod';

// Indian phone number validation (10 digits starting with 6, 7, 8, or 9)
export const phoneNumberSchema = z
  .string()
  .regex(/^[6-9]\d{9}$/, 'Please enter a valid 10-digit Indian phone number');

export const signupSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  phone_number: phoneNumberSchema,
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

export const signinSchema = z.object({
  phone_number: phoneNumberSchema,
  password: z.string().min(1, 'Password is required'),
});

export type SignupFormData = z.infer<typeof signupSchema>;
export type SigninFormData = z.infer<typeof signinSchema>;
