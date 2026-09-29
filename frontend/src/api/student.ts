import { getStudentToken, setStudentToken, studentApiClient } from "./client";
import type {
  StudentProfile,
  StudentProfileCreated,
  StudentProfilePayload,
  StudentSkill,
} from "@/types/api";

export const studentApi = {
  token: getStudentToken,
  createProfile: (payload: StudentProfilePayload) =>
    studentApiClient
      .post<StudentProfileCreated>("/student/profiles", payload)
      .then((response) => {
        setStudentToken(response.data.access_token);
        return response.data.profile;
      }),
  getProfile: () =>
    studentApiClient
      .get<StudentProfile>("/student/profile")
      .then((response) => response.data),
  getSkills: () =>
    studentApiClient
      .get<StudentSkill[]>("/student/profile/skills")
      .then((response) => response.data),
  updateProfile: (payload: Partial<StudentProfilePayload>) =>
    studentApiClient
      .patch<StudentProfile>("/student/profile", payload)
      .then((response) => response.data),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("resume", file);
    return studentApiClient
      .post<StudentProfile>("/student/profile/resume", form)
      .then((response) => response.data);
  },
};
