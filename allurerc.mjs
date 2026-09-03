export default {
  name: "QA 자동화 테스트 리포트",
  plugins: {
    awesome: {
      options: {
        singleFile: true,          // 리포트를 index.html 하나로 묶어서 생성
        groupBy: ["feature"],      // 트리를 파일명(suite) 대신 화면(feature) 기준으로 묶음
        reportLanguage: "ko",
        theme: "auto",
      },
    },
  },
};
